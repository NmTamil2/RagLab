"""HTTP routes for health checks.

The router is thin on purpose: it defines the URL, the response model and the
error behaviour, then delegates the real work to the service layer.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models.health import HealthResponse
from app.services import health_service

logger = logging.getLogger(__name__)

# tags=["health"] groups this endpoint in the auto-generated docs at /docs
router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check that the backend is alive",
)
def read_health() -> HealthResponse:
    """Return the backend's current status.

    The frontend calls this on load to prove that React can reach FastAPI.
    """
    try:
        return health_service.get_health_status()
    except Exception:  # pragma: no cover - defensive: nothing here should fail
        # Log the real traceback for us, return a safe message to the client.
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed",
        )
