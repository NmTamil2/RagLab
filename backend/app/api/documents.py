"""HTTP routes for document management.

The route stays thin: it receives the file, calls the service, and translates
the service's exceptions into the right HTTP status codes. All the storage
rules live in the service.
"""

import logging

from fastapi import APIRouter, File, HTTPException, Path, UploadFile, status

from app.models.document import DocumentExtraction, DocumentMetadata
from app.services import document_parser, document_service
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

    return DocumentExtraction(
        document_id=metadata.document_id,
        filename=metadata.filename,
        page_count=len(pages),
        pages=pages,
    )
