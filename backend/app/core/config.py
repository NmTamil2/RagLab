"""Application configuration.

Every setting comes from an environment variable (or a .env file next to the
backend folder). Nothing is hard-coded, so the same code runs on your laptop
and on a server without editing Python files.
"""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The backend/ folder, found relative to this file:
#   config.py -> core/ -> app/ -> backend/
# Used to turn relative paths from .env into absolute ones, so the server
# behaves the same no matter which directory you launch it from.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed configuration for the RAGLab backend.

    Each attribute below maps to an environment variable of the same name,
    case-insensitively. Example: APP_NAME=... in .env sets `app_name`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unrelated variables already in your shell
    )

    # --- Identity -----------------------------------------------------------
    app_name: str = "RAGLab API"
    app_version: str = "0.4.0"
    environment: str = "development"

    # --- CORS ---------------------------------------------------------------
    # Browsers block a page on localhost:5173 from calling localhost:8000
    # unless the API explicitly allows that origin. This is that allow-list.
    # In .env it is written as a comma-separated string, e.g.
    #   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Document storage ---------------------------------------------------
    # Where uploaded PDFs are written. Relative paths are resolved against
    # backend/. Kept outside app/ so user data never mixes with source code.
    documents_dir: str = "storage/documents"

    # Upload size ceiling. Without one, a single huge request could fill the
    # disk, so the limit is enforced while streaming, not after.
    max_upload_size_mb: int = 20

    # --- Chunking -----------------------------------------------------------
    # Chunk size and overlap are the two numbers we will spend the rest of the
    # project tuning, so they live here rather than inside the chunking code.
    # Changing them means editing .env and restarting — never editing Python.
    #
    # Both are measured in characters, not words or tokens. Characters are what
    # the algorithm actually counts, so the setting means exactly what it says.

    # How many characters of text go into one chunk.
    chunk_size: int = Field(default=500, gt=0)

    # How many characters each chunk repeats from the end of the previous one.
    chunk_overlap: int = Field(default=50, ge=0)

    @model_validator(mode="after")
    def _check_overlap_fits_inside_chunk(self) -> "Settings":
        """Reject an overlap that is not smaller than the chunk size.

        With overlap >= size the window would never move forward (or would move
        backwards), so chunking would loop forever. Catching it here means a bad
        .env stops the server at startup with a clear message, instead of
        producing a confusing 500 on the first request hours later.
        """
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) must be smaller than "
                f"CHUNK_SIZE ({self.chunk_size})."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Split the comma-separated origins string into a clean list."""
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def documents_path(self) -> Path:
        """Absolute path to the folder holding uploaded documents."""
        path = Path(self.documents_dir)
        return path if path.is_absolute() else BACKEND_DIR / path

    @property
    def max_upload_size_bytes(self) -> int:
        """The upload limit in bytes, which is what we compare against."""
        return self.max_upload_size_mb * 1024 * 1024


# A single shared instance, imported wherever configuration is needed.
settings = Settings()
