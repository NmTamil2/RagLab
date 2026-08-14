"""HTTP routes for document management.

The route stays thin: it receives the file, calls the service, and translates
the service's exceptions into the right HTTP status codes. All the storage
rules live in the service.
"""

import logging

from fastapi import APIRouter, File, HTTPException, Path, Query, UploadFile, status

from app.models.chunk import DocumentChunks
from app.models.document import DocumentExtraction, DocumentMetadata, PageText
from app.services import chunking_service, document_parser, document_service
from app.services.chunking_service import InvalidChunkConfigError
from app.services.document_parser import (
    CorruptedPdfError,
    DocumentParseError,
    NoExtractableTextError,
    ProtectedPdfError,
)
from app.services.document_service import (
    DocumentFileMissingError,
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF document",
)
async def upload_document(file: UploadFile = File(...)) -> DocumentMetadata:
    """Accept a PDF, store it, and return its metadata.

    The parameter name `file` is what the frontend must use as the form field
    name. FastAPI returns 422 automatically when it is missing.
    """
    try:
        return await document_service.save_document(file)

    except DocumentValidationError as error:
        # The client sent something we cannot accept — their side to fix.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    except DocumentTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(error),
        )
    except DocumentStorageError as error:
        # Our side failed. The real traceback is already logged in the service.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )


def _load_document_pages(
    document_id: str,
) -> tuple[DocumentMetadata, list[PageText]]:
    """Find a stored document and extract its text, or raise the right HTTP error.

    Both routes below start the same way — look up the document, check the file
    is really on disk, parse it — and both need the same five failures mapped to
    the same status codes. Keeping that in one place means the two endpoints can
    never drift apart and start reporting the same problem differently.
    """
    try:
        metadata = document_service.load_document_metadata(document_id)
        pdf_path = document_service.get_document_file(document_id)
        pages = document_parser.extract_pages(pdf_path)

    except (DocumentNotFoundError, DocumentFileMissingError) as error:
        # Nothing to work with — the client asked for something that is not here.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except (CorruptedPdfError, ProtectedPdfError, NoExtractableTextError) as error:
        # The document exists and the request was well-formed, but the file
        # cannot yield text. 422 says exactly that: understood, but unprocessable.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    except DocumentParseError as error:
        # Unexpected parser failure. The traceback is already logged in the parser.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        )

    return metadata, pages


@router.post(
    "/{document_id}/extract",
    response_model=DocumentExtraction,
    summary="Extract the text of an uploaded PDF, page by page",
)
def extract_document_text(
    document_id: str = Path(description="ID returned when the document was uploaded"),
) -> DocumentExtraction:
    """Read a stored PDF and return its text, one entry per page.

    POST rather than GET: this triggers real work on the server — opening and
    parsing the whole file — instead of handing back a stored resource. GET is
    meant to be cheap and freely repeatable, and browsers and proxies may cache
    or pre-fetch it. POST also leaves `/documents/{id}` free to mean "the
    document itself" later, and is where the next milestones will naturally
    hang chunking and embedding onto the same call.

    The route itself stays free of PDF logic: it looks the document up, checks
    the file is there, hands the path to the parser, and maps failures to
    status codes.

    Declared with `def` rather than `async def` on purpose: parsing is blocking
    CPU work, and FastAPI runs plain functions in a worker thread, so one large
    PDF cannot freeze every other request.
    """
    metadata, pages = _load_document_pages(document_id)

    return DocumentExtraction(
        document_id=metadata.document_id,
        filename=metadata.filename,
        page_count=len(pages),
        pages=pages,
    )


@router.post(
    "/{document_id}/chunk",
    response_model=DocumentChunks,
    summary="Split an uploaded PDF into overlapping text chunks",
)
def chunk_document(
    document_id: str = Path(description="ID returned when the document was uploaded"),
    chunk_size: int | None = Query(
        default=None,
        description=(
            "Characters per chunk. Omit to use the server's configured "
            "CHUNK_SIZE. Provided so different settings can be compared "
            "without restarting the backend."
        ),
        examples=[500],
    ),
    chunk_overlap: int | None = Query(
        default=None,
        description=(
            "Characters each chunk repeats from the previous one. Omit to use "
            "the server's configured CHUNK_OVERLAP. Must be smaller than "
            "chunk_size."
        ),
        examples=[50],
    ),
) -> DocumentChunks:
    """Parse a stored PDF and return its text split into chunks.

    The flow is a straight line through the layers, and this function does none
    of the work itself:

        route -> document_service (find it)
              -> document_parser  (page-level text)
              -> chunking_service (chunks)

    Chunking is not cached or stored yet — each call re-parses and re-chunks the
    PDF. That is exactly what you want while learning: change the settings, call
    again, see different chunks. Persisting them belongs with the vector store,
    in a later milestone.

    `def` rather than `async def` for the same reason as the extract route: this
    is blocking CPU work, so FastAPI should run it in a worker thread.
    """
    # Validate the configuration before touching the disk. If the numbers are
    # wrong there is no point parsing a 40-page PDF first.
    try:
        config = chunking_service.config_from_settings(chunk_size, chunk_overlap)
    except InvalidChunkConfigError as error:
        # The client asked for something impossible — 400, their side to fix.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    metadata, pages = _load_document_pages(document_id)

    chunks = chunking_service.chunk_pages(pages, metadata.document_id, config)

    return DocumentChunks(
        document_id=metadata.document_id,
        filename=metadata.filename,
        page_count=len(pages),
        chunk_count=len(chunks),
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        chunks=chunks,
    )
