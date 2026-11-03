"""Public API schemas for the Naadi backend."""

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Frontend-ready successful Prisma transcription response."""

    success: bool = True
    request_id: str | None = None
    transcript: str
    detected_language_code: str | None = None
    model: str | None = None
    processing_time: float | None = Field(default=None, ge=0)
    end_to_end_latency: float | None = Field(default=None, ge=0)


class ErrorDetail(BaseModel):
    """Safe, stable error detail returned by Naadi."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Consistent unsuccessful API response."""

    success: bool = False
    error: ErrorDetail


class HealthResponse(BaseModel):
    """Safe service/dependency status response."""

    status: str
    service: str
    version: str
    gnani_api_key_configured: bool
    prisma_model: str
