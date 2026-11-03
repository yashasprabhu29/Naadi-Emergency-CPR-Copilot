"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    The API key is intentionally not represented in logs or API responses.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
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

    @property
    def gnani_api_url(self) -> str:
        """Return the configured STT URL without exposing credentials."""

        return f"{self.gnani_base_url.rstrip('/')}/{self.gnani_stt_path.lstrip('/')}"

    @property
    def has_gnani_api_key(self) -> bool:
        """Whether a non-empty API key is configured."""

        return bool(self.gnani_api_key and self.gnani_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings."""

    return Settings()
