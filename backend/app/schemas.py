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
    """Single utterance for emergency analysis with full context."""

    text: str = Field(..., min_length=1, description="Utterance text")
    speaker: str | None = Field(
        default=None,
        description="Speaker role: 'caller', 'operator', or None if unknown",
    )
    utterance_index: int = Field(default=0, ge=0, description="Position in conversation")
    utterance_id: str | None = Field(
        default=None,
        description="Unique identifier (auto-generated if not provided)",
    )
    timestamp: float | None = Field(
        default=None,
        ge=0,
        description="Optional timestamp in seconds from call start",
    )
    language: str | None = Field(
        default=None,
        description="Detected language code (e.g., 'kn', 'en', 'hi', 'mixed')",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional transcription confidence score",
    )
    source: str = Field(
        default="manual",
        description="Source: 'manual', 'diarization', 'sentence_boundary'",
    )


class EmergencyAnalysisRequest(BaseModel):
    """Request to analyze transcript for emergency indicators."""

    utterances: list[UtteranceInput] = Field(
        ..., min_length=1, description="Chronologically ordered utterances"
    )


class MatchedIndicatorResponse(BaseModel):
    """Detected emergency phrase in the transcript with full traceability."""

    phrase: str
    category: str
    utterance_index: int
    utterance_id: str
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



# TTS Schemas
class TTSRequest(BaseModel):
    """Request to synthesize a predefined emergency prompt."""

    prompt_id: str = Field(
        ...,
        description="ID of predefined emergency prompt",
        examples=["start_cpr_kannada", "check_breathing_hindi"],
    )
    voice: str | None = Field(
        default=None,
        description="Optional voice override (defaults to language-appropriate voice)",
        examples=["Chetana", "Kalpana", "Shivani"],
    )
    speed: float = Field(
        default=1.0,
        ge=0.85,
        le=1.15,
        description="Playback speed multiplier (0.85-1.15)",
    )


class TTSPromptsResponse(BaseModel):
    """Response listing available emergency prompts."""

    prompts: dict[str, dict[str, str]] = Field(
        ...,
        description="Dictionary mapping prompt_id to {language, description}",
    )
    model: str = Field(
        ...,
        description="TTS model used (timbre-v3.0)",
        examples=["timbre-v3.0"],
    )
