"""RAGLab backend entry point.

This file wires the application together and nothing else:
  1. create the FastAPI app
  2. allow the React dev server to call it (CORS)
  3. register routers
  4. install a catch-all error handler

Run it with:  uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Educational, production-style RAG application. Step 1: foundation.",
)

# --- CORS -------------------------------------------------------------------
# In development the frontend (http://localhost:5173) and the backend
# (http://localhost:8000) are different origins, so the browser requires the
# backend to opt in. We list exact origins instead of "*" so this stays safe
# when credentials/cookies are added later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ----------------------------------------------------------------
# Every route lives under /api so the URL space stays tidy as features grow.
app.include_router(health.router, prefix="/api")


# --- Error handling ---------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Turn any unexpected crash into a clean JSON 500 instead of an HTML page.

    The frontend can then always parse the response, and the stack trace stays
    in our server logs rather than being shown to the user.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/", tags=["root"], summary="API landing information")
def read_root() -> dict[str, str]:
    """A friendly pointer for anyone who opens the backend URL directly."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }
