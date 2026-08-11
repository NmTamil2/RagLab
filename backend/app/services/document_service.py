"""Document storage logic.

Like the health service, this module knows nothing about HTTP. It raises plain
Python exceptions describing *what went wrong*, and the API layer decides which
status code that maps to. That split keeps the rules testable and lets a future
milestone reuse this from a script or background job.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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
    destination = settings.documents_path / f"{document_id}.pdf"
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

    return DocumentMetadata(
        document_id=document_id,
        filename=original_filename,
        file_type="pdf",
        file_size=file_size,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
    )
