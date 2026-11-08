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


class UtteranceInput(BaseModel):
    """Single utterance for emergency analysis."""

    text: str = Field(..., min_length=1, description="Utterance text")
    speaker: str | None = Field(
        default=None,
        description="Speaker role: 'caller', 'operator', or None if unknown",
    )
    utterance_index: int = Field(default=0, ge=0, description="Position in conversation")


class EmergencyAnalysisRequest(BaseModel):
    """Request to analyze transcript for emergency indicators."""

    utterances: list[UtteranceInput] = Field(
        ..., min_length=1, description="Chronologically ordered utterances"
    )


class MatchedIndicatorResponse(BaseModel):
    """Detected emergency phrase in the transcript."""

    phrase: str
    category: str
    utterance_index: int
    utterance_text: str
    speaker: str | None


class EmergencyAnalysisResponse(BaseModel):
    """Structured emergency detection result."""

    status: str = Field(..., description="Detection status: no_indicator, review_required, potential_emergency")
    risk_category: str = Field(..., description="Risk classification: none, uncertain, cardiac_respiratory")
    explanation: str = Field(..., description="Human-readable explanation of the detection result")
    matched_indicators: list[MatchedIndicatorResponse]
    contradictory_evidence: list[str]
    rule_identifiers: list[str]
    requires_operator_confirmation: bool
    uncertainty_notes: list[str]
    detector_version: str
