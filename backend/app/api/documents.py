"""HTTP routes for document management.

The route stays thin: it receives the file, calls the service, and translates
the service's exceptions into the right HTTP status codes. All the storage
rules live in the service.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.document import DocumentMetadata
from app.services import document_service
from app.services.document_service import (
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
