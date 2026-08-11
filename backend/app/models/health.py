"""Response models for the health endpoint.

Declaring the response shape as a Pydantic model gives us three things for
free: validation, a documented schema in /docs, and a single place to change
the contract the frontend depends on.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """What GET /api/health returns."""

    status: str = Field(
        description="'ok' when the backend is running and able to answer.",
        examples=["ok"],
    )
    service: str = Field(
        description="Human-readable name of this service.",
        examples=["RAGLab API"],
    )
    version: str = Field(
        description="Version of the backend application.",
        examples=["0.1.0"],
    )
    environment: str = Field(
        description="Which environment this instance is running in.",
        examples=["development"],
    )
    timestamp: str = Field(
        description="UTC time the health check was produced, in ISO 8601.",
        examples=["2026-01-01T12:00:00+00:00"],
    )
