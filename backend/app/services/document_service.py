"""Document storage logic.

Like the health service, this module knows nothing about HTTP. It raises plain
Python exceptions describing *what went wrong*, and the API layer decides which
status code that maps to. That split keeps the rules testable and lets a future
milestone reuse this from a script or background job.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.models.document import DocumentMetadata

logger = logging.getLogger(__name__)

# Every real PDF starts with these bytes. Checking them means a renamed .exe
# cannot sneak through just because its name ends in ".pdf".
PDF_MAGIC_BYTES = b"%PDF-"

# Read the upload in 1 MB pieces instead of all at once, so memory use stays
# flat no matter how large the file is.
CHUNK_SIZE = 1024 * 1024


class DocumentValidationError(Exception):
    """The upload was rejected: wrong type, empty, or missing."""


class DocumentTooLargeError(Exception):
    """The upload exceeded the configured size limit."""


class DocumentStorageError(Exception):
    """The file was valid but could not be written to disk."""


class DocumentNotFoundError(Exception):
    """No document with the requested ID has been uploaded."""


class DocumentFileMissingError(Exception):
    """The document is known, but its PDF is gone from storage."""


def _pdf_path(document_id: str) -> Path:
    """Where the PDF for this document ID lives."""
    return settings.documents_path / f"{document_id}.pdf"


def _metadata_path(document_id: str) -> Path:
    """Where the small JSON record describing that PDF lives.

    The PDF itself cannot tell us the name the user gave it — we rename on
    upload for safety — so the original filename is kept in a sidecar file next
    to it. A database would be nicer, and arrives in a later milestone; one
    small JSON file per document is enough until then, and it survives a
    server restart, which an in-memory dict would not.
    """
    return settings.documents_path / f"{document_id}.json"


def _is_valid_document_id(document_id: str) -> bool:
    """Check that an ID is one of ours before it is used to build a path.

    IDs arrive from the URL, so they are untrusted input. Requiring a real UUID
    means a value like "../../../etc/passwd" is rejected outright instead of
    being turned into a filesystem path.
    """
    try:
        UUID(document_id)
    except ValueError:
        return False
    return True


def _delete_partial_file(path: Path) -> None:
    """Remove a half-written file after a failed upload.

    Without this, a rejected upload would leave junk behind in storage.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove partial upload at %s", path)


async def save_document(upload_file: UploadFile) -> DocumentMetadata:
    """Validate an uploaded PDF, store it, and return its metadata.

    Raises:
        DocumentValidationError: not a PDF, empty, or no filename.
        DocumentTooLargeError: bigger than MAX_UPLOAD_SIZE_MB.
        DocumentStorageError: the disk write failed.
    """
    original_filename = (upload_file.filename or "").strip()

    if not original_filename:
        raise DocumentValidationError("No file was provided.")

    if not original_filename.lower().endswith(".pdf"):
        raise DocumentValidationError(
            f"Only PDF files are supported. '{original_filename}' is not a PDF."
        )

    # The stored name is the generated ID, never the user's filename. A name
    # like "../../app/main.py" would otherwise let an upload overwrite our
    # source code, and two people uploading "report.pdf" would collide.
    document_id = str(uuid4())
    destination = _pdf_path(document_id)
    file_size = 0

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as stored_file:
            is_first_chunk = True

            while chunk := await upload_file.read(CHUNK_SIZE):
                if is_first_chunk:
                    if not chunk.startswith(PDF_MAGIC_BYTES):
                        raise DocumentValidationError(
                            "The file is not a valid PDF. It may be renamed or corrupted."
                        )
                    is_first_chunk = False

                file_size += len(chunk)
                if file_size > settings.max_upload_size_bytes:
                    raise DocumentTooLargeError(
                        f"File is larger than the {settings.max_upload_size_mb} MB limit."
                    )

                stored_file.write(chunk)

        if file_size == 0:
            raise DocumentValidationError("The selected file is empty.")

    except (DocumentValidationError, DocumentTooLargeError):
        _delete_partial_file(destination)
        raise
    except OSError as error:
        _delete_partial_file(destination)
        logger.exception("Failed to write upload to %s", destination)
        raise DocumentStorageError("Could not save the file on the server.") from error

    logger.info("Stored document %s (%s, %d bytes)", document_id, original_filename, file_size)

    metadata = DocumentMetadata(
        document_id=document_id,
        filename=original_filename,
        file_type="pdf",
        file_size=file_size,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
    )

    _save_metadata(metadata)

    return metadata


def _save_metadata(metadata: DocumentMetadata) -> None:
    """Record the document's details next to the stored PDF.

    A failure here is logged but not raised: the PDF is already safely on disk,
    and losing the sidecar only costs us the original filename, which
    `load_document_metadata` can fall back from.
    """
    try:
        _metadata_path(metadata.document_id).write_text(
            metadata.model_dump_json(indent=2), encoding="utf-8"
        )
    except OSError:
        logger.warning("Could not write metadata for document %s", metadata.document_id)


def load_document_metadata(document_id: str) -> DocumentMetadata:
    """Look up a previously uploaded document by its ID.

    Raises:
        DocumentNotFoundError: the ID is malformed or nothing was uploaded
            under it.
    """
    if not _is_valid_document_id(document_id):
        raise DocumentNotFoundError(f"'{document_id}' is not a valid document ID.")

    metadata_file = _metadata_path(document_id)

    if metadata_file.is_file():
        try:
            return DocumentMetadata.model_validate_json(
                metadata_file.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            # Unreadable or hand-edited sidecar: fall through to the PDF below
            # rather than failing a request we can still answer.
            logger.warning("Ignoring unreadable metadata for document %s", document_id)

    pdf_file = _pdf_path(document_id)

    if not pdf_file.is_file():
        raise DocumentNotFoundError(f"No document found with ID '{document_id}'.")

    # The PDF exists without a usable sidecar — either it was uploaded before
    # metadata was recorded, or the sidecar was lost. Rebuild what the file
    # itself can tell us so the document stays usable.
    stats = pdf_file.stat()

    return DocumentMetadata(
        document_id=document_id,
        filename=pdf_file.name,
        file_type="pdf",
        file_size=stats.st_size,
        uploaded_at=datetime.fromtimestamp(stats.st_mtime, timezone.utc).isoformat(),
    )


def get_document_file(document_id: str) -> Path:
    """Return the path of a document's PDF, confirming it is really there.

    Metadata can outlive the file it describes — someone may empty the storage
    folder — so existence is checked separately from the lookup above.

    Raises:
        DocumentFileMissingError: the ID is malformed, or the PDF is not on disk.
    """
    if not _is_valid_document_id(document_id):
        raise DocumentFileMissingError(f"'{document_id}' is not a valid document ID.")

    pdf_file = _pdf_path(document_id)

    if not pdf_file.is_file():
        raise DocumentFileMissingError(
            f"The stored file for document '{document_id}' is missing."
        )

    return pdf_file
