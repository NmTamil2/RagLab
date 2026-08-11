"""Health-check business logic.

This module is deliberately free of FastAPI imports. It answers the question
"is this service healthy, and what is it?" as plain Python, which keeps it easy
to test and easy to reuse. Later milestones will add checks here (for example:
can we reach ChromaDB?) without touching the HTTP layer.
"""

from datetime import datetime, timezone

from app.core.config import settings
from app.models.health import HealthResponse


def get_health_status() -> HealthResponse:
    """Build the current health report for the backend."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
