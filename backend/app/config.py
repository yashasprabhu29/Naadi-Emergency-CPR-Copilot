"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find .env file at project root regardless of where the script runs
def _find_env_file() -> Path:
    """Locate .env file at project root."""
    # Start from this config.py file location
    config_dir = Path(__file__).parent  # backend/app/
    backend_dir = config_dir.parent  # backend/
    project_root = backend_dir.parent  # project root
    return project_root / ".env"


# The value shipped in .env.example. Treated as "no key" so a copied template
# fails with a clear message instead of a 401 from Gnani.
PLACEHOLDER_API_KEY = "your_gnani_api_key_here"

# Shown whenever the key is missing. Keep in sync with README.
MISSING_KEY_MESSAGE = (
    "GNANI_API_KEY is not configured. Put your key in the file named .env "
    "in the project folder (not .env.example), save it, then restart the backend."
)


class Settings(BaseSettings):
    """Runtime configuration.

    The API key is intentionally not represented in logs or API responses.
    """

    model_config = SettingsConfigDict(
        env_file=str(_find_env_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Naadi"
    app_version: str = "0.1.0"
    environment: str = "development"

    gnani_api_key: str | None = Field(default=None, validation_alias="GNANI_API_KEY")
    gnani_base_url: str = Field(
        default="https://api.vachana.ai", validation_alias="GNANI_BASE_URL"
    )
    gnani_stt_path: str = Field(default="/stt/v3", validation_alias="GNANI_STT_PATH")
    gnani_model: str = Field(default="prisma-v3.0", validation_alias="GNANI_MODEL")
    gnani_language_code: str = Field(
        default="kn-IN,en-IN", validation_alias="GNANI_LANGUAGE_CODE"
    )
    gnani_format: str = Field(default="codemix", validation_alias="GNANI_FORMAT")
    gnani_timeout_seconds: float = Field(
        default=60.0, gt=0, validation_alias="GNANI_TIMEOUT_SECONDS"
    )
    max_upload_size_bytes: int = Field(
        default=25 * 1024 * 1024,
        gt=0,
        validation_alias="MAX_UPLOAD_SIZE_BYTES",
    )
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    naadi_db_path: Path = Field(
        default=_find_env_file().parent / "data" / "naadi.sqlite3",
        validation_alias="NAADI_DB_PATH",
    )
    # Realtime streaming (Gnani Prisma WebSocket)
    gnani_stream_url: str = Field(
        default="wss://api.vachana.ai/stt/v3/stream", validation_alias="GNANI_STREAM_URL"
    )
    # Public deployment protection. Leave the code empty for local development.
    naadi_access_code: str | None = Field(default=None, validation_alias="NAADI_ACCESS_CODE")
    naadi_daily_transcriptions: int = Field(default=150, ge=0, validation_alias="NAADI_DAILY_TRANSCRIPTIONS")
    naadi_daily_live_minutes: int = Field(default=60, ge=0, validation_alias="NAADI_DAILY_LIVE_MINUTES")
    naadi_daily_tts: int = Field(default=60, ge=0, validation_alias="NAADI_DAILY_TTS")
    # Built frontend to serve from the same origin (set in the Docker image).
    naadi_static_dir: Path | None = Field(default=None, validation_alias="NAADI_STATIC_DIR")
    # One locale only; defaults to the first code in GNANI_LANGUAGE_CODE.
    gnani_stream_language_code: str | None = Field(default=None, validation_alias="GNANI_STREAM_LANGUAGE_CODE")
    stream_max_seconds: int = Field(default=600, gt=0, le=840, validation_alias="STREAM_MAX_SECONDS")
    stream_max_sessions: int = Field(default=1, gt=0, le=10, validation_alias="STREAM_MAX_SESSIONS")

    @property
    def gnani_api_url(self) -> str:
        """Return the configured STT URL without exposing credentials."""

        return f"{self.gnani_base_url.rstrip('/')}/{self.gnani_stt_path.lstrip('/')}"

    @property
    def has_gnani_api_key(self) -> bool:
        """Whether a real API key is configured (the .env.example placeholder does not count)."""

        key = (self.gnani_api_key or "").strip()
        return bool(key) and key != PLACEHOLDER_API_KEY

    @property
    def cors_origins(self) -> list[str]:
        """Return configured explicit origins for browser development."""

        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()
