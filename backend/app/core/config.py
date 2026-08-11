"""Application configuration.

Every setting comes from an environment variable (or a .env file next to the
backend folder). Nothing is hard-coded, so the same code runs on your laptop
and on a server without editing Python files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    app_version: str = "0.1.0"
    environment: str = "development"

    # --- CORS ---------------------------------------------------------------
    # Browsers block a page on localhost:5173 from calling localhost:8000
    # unless the API explicitly allows that origin. This is that allow-list.
    # In .env it is written as a comma-separated string, e.g.
    #   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """Split the comma-separated origins string into a clean list."""
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


# A single shared instance, imported wherever configuration is needed.
settings = Settings()
