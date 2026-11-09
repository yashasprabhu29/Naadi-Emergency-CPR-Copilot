"""FastAPI application and staged-audio transcription endpoint."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.schemas import (
    EmergencyAnalysisRequest,
    EmergencyAnalysisResponse,
    ErrorResponse,
    HealthResponse,
    MatchedIndicatorResponse,
    TranscriptionResponse,
)
from backend.app.services.emergency_detector import EmergencyDetector, Utterance
from backend.app.services.prisma_client import (
    AudioValidationError,
    PrismaAPIError,
    PrismaClient,
    PrismaConfigurationError,
    PrismaNetworkError,
    SUPPORTED_AUDIO_EXTENSIONS,
    TranscriptionResult,
)

settings = get_settings()
logger = logging.getLogger("naadi.transcriptions")

SUPPORTED_CONTENT_TYPES: dict[str, frozenset[str]] = {
    ".wav": frozenset({"audio/wav", "audio/x-wav", "audio/wave"}),
    ".mp3": frozenset({"audio/mpeg", "audio/mp3"}),
    ".ogg": frozenset({"audio/ogg", "application/ogg"}),
    ".flac": frozenset({"audio/flac", "audio/x-flac"}),
    ".aac": frozenset({"audio/aac", "audio/x-aac"}),
    ".m4a": frozenset({"audio/mp4", "audio/x-m4a"}),
}

app = FastAPI(
    title="Naadi",
    description=(
        "Emergency call-taker copilot backend. This milestone accepts staged "
        "audio and delegates transcription to Gnani Prisma v3.0."
    ),
    version=settings.app_version,
)
from backend.app.access import (  # noqa: E402
    ACCESS_HEADER,
    AccessCodeMiddleware,
    SecurityHeadersMiddleware,
    access_required,
    daily_limit_response,
    quota,
)
from backend.app.access import router as access_router  # noqa: E402

# Order matters: the last middleware added runs first. CORS stays outermost so
# that 401 responses from the access check still carry CORS headers.
app.add_middleware(AccessCodeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Accept", "Content-Type", ACCESS_HEADER],
)

# Access check, saved-call log (SQLite) and live microphone relay (Gnani realtime STT).
from backend.app.calls_api import router as calls_router  # noqa: E402
from backend.app.streaming import router as streaming_router  # noqa: E402

app.include_router(access_router)
app.include_router(calls_router)
app.include_router(streaming_router)

def _find_static_dir() -> Path | None:
    """The built frontend: NAADI_STATIC_DIR if set, else frontend/dist in the project."""

    project_root = Path(__file__).resolve().parents[2]
    candidates = [settings.naadi_static_dir, project_root / "frontend" / "dist"]
    for candidate in candidates:
        if candidate is None:
            continue
        candidate = candidate if candidate.is_absolute() else project_root / candidate
        if (candidate / "index.html").is_file() and (candidate / "assets").is_dir():
            return candidate
    return None


_STATIC_DIR = _find_static_dir()
logger.info("Serving built frontend from %s", _STATIC_DIR or "nowhere (API only)")


if _STATIC_DIR is None:
    # Without a built frontend, "/" describes the API. In the Docker image it serves the site.
    @app.get("/")
    def metadata() -> dict[str, str]:
        """Return safe application metadata."""

        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "ok",
        }


@app.get("/health")
def health() -> dict[str, object]:
    """Return process health and non-secret configuration status."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "gnani_api_key_configured": settings.has_gnani_api_key,
        "prisma_model": settings.gnani_model,
        "access_required": access_required(),
    }


def get_prisma_client() -> PrismaClient:
    """Provide the Prisma adapter; tests can override this dependency."""

    return PrismaClient(settings)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Create the public error envelope without exposing implementation details."""

    body = ErrorResponse(error={"code": code, "message": message}).model_dump()
    return JSONResponse(status_code=status_code, content=body)


def _upstream_status(status_code: int) -> int:
    """Map client errors to safe HTTP statuses while preserving API statuses."""

    if 400 <= status_code <= 599:
        return status_code
    return status.HTTP_502_BAD_GATEWAY


async def _write_upload_to_temp(upload: UploadFile, suffix: str) -> tuple[str, int]:
    """Stream an upload to a temporary file, enforcing the configured size limit."""

    temporary = tempfile.NamedTemporaryFile(
        mode="wb", prefix="naadi-upload-", suffix=suffix, delete=False
    )
    path = temporary.name
    size = 0
    try:
        with temporary:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    raise ValueError("The uploaded file exceeds the configured size limit.")
                temporary.write(chunk)
        return path, size
    except Exception:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        raise


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
def api_health() -> HealthResponse:
    """Return API service and local Gnani configuration status.

    This endpoint does not call Gnani and therefore does not consume credits.
    """

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        gnani_api_key_configured=settings.has_gnani_api_key,
        prisma_model=settings.gnani_model,
        access_required=access_required(),
    )


@app.post(
    "/api/v1/transcriptions",
    response_model=TranscriptionResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    tags=["transcriptions"],
    summary="Transcribe a staged emergency-call recording",
    description=(
        "Accepts one WAV, MP3, OGG, FLAC, AAC or M4A recording, validates it, "
        "temporarily stores it, and sends it to Gnani Prisma v3.0. REST audio "
        "is limited to 30 seconds by Gnani. The default local upload limit is "
        "25 MiB. Uploaded audio is deleted after the request."
    ),
    responses={
        200: {
            "description": "Successful Prisma transcription",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "request_id": "request-id-from-gnani",
                        "transcript": "ನನಗೆ chest pain ಇದೆ",
                        "detected_language_code": "kn-IN",
                        "model": "prisma-v3.0",
                        "processing_time": 0.42,
                        "end_to_end_latency": 0.55,
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid or empty audio"},
        401: {"model": ErrorResponse, "description": "Gnani rejected the API key"},
        402: {"model": ErrorResponse, "description": "Gnani account has insufficient credit"},
        403: {"model": ErrorResponse, "description": "Gnani service scope is not allowed"},
        429: {"model": ErrorResponse, "description": "Gnani rate or concurrency limit"},
        413: {"model": ErrorResponse, "description": "Upload exceeds local size limit"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        500: {"model": ErrorResponse, "description": "Gnani transcription failure"},
        502: {"model": ErrorResponse, "description": "Network or malformed upstream response"},
        503: {"model": ErrorResponse, "description": "Missing local API configuration"},
        504: {"model": ErrorResponse, "description": "Upstream timeout"},
    },
)
async def create_transcription(
    audio: UploadFile | None = File(
        default=None,
        description=(
            "Audio recording. Supported extensions: .wav, .mp3, .ogg, .flac, "
            ".aac and .m4a. Maximum REST duration: 30 seconds."
        ),
    ),
    prisma: PrismaClient = Depends(get_prisma_client),
) -> TranscriptionResponse | JSONResponse:
    """Validate a staged upload and return its Prisma transcription."""

    if audio is None or not audio.filename:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "MISSING_AUDIO",
            "Upload one audio file using the 'audio' form field.",
        )

    suffix = Path(audio.filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "UNSUPPORTED_AUDIO_EXTENSION",
            "Supported audio extensions are .wav, .mp3, .ogg, .flac, .aac and .m4a.",
        )

    content_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in SUPPORTED_CONTENT_TYPES[suffix]:
        return _error_response(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "UNSUPPORTED_MEDIA_TYPE",
            f"Content type '{content_type or 'missing'}' is not valid for {suffix}.",
        )

    temporary_path: str | None = None
    try:
        try:
            temporary_path, size = await _write_upload_to_temp(audio, suffix)
        except ValueError as exc:
            logger.warning("Rejected oversized upload: suffix=%s", suffix)
            return _error_response(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "UPLOAD_TOO_LARGE",
                str(exc),
            )

        if size == 0:
            logger.warning("Rejected empty upload: suffix=%s", suffix)
            return _error_response(
                status.HTTP_400_BAD_REQUEST,
                "EMPTY_AUDIO",
                "The uploaded audio file is empty.",
            )

        if not quota.try_consume("transcriptions"):
            return daily_limit_response("transcriptions")

        try:
            # PrismaClient is synchronous because it also supports the CLI. Run
            # it off the event loop so concurrent FastAPI requests remain responsive.
            result: TranscriptionResult = await run_in_threadpool(
                prisma.transcribe, temporary_path
            )
        except PrismaConfigurationError as exc:
            logger.error("Prisma configuration is unavailable")
            return _error_response(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "GNANI_NOT_CONFIGURED",
                str(exc),
            )
        except AudioValidationError as exc:
            logger.warning("Rejected invalid audio: suffix=%s", suffix)
            return _error_response(status.HTTP_400_BAD_REQUEST, "INVALID_AUDIO", str(exc))
        except PrismaAPIError as exc:
            logger.warning("Prisma API error: status=%s code=%s", exc.status_code, exc.error_code)
            return _error_response(
                _upstream_status(exc.status_code), exc.error_code, exc.message
            )
        except PrismaNetworkError as exc:
            message = str(exc)
            if "timed out" in message.lower():
                logger.warning("Prisma request timed out")
                return _error_response(status.HTTP_504_GATEWAY_TIMEOUT, "UPSTREAM_TIMEOUT", message)
            logger.warning("Prisma network request failed")
            return _error_response(status.HTTP_502_BAD_GATEWAY, "UPSTREAM_NETWORK_ERROR", message)

        logger.info(
            "Prisma transcription completed: model=%s request_id=%s bytes=%s",
            result.model or "unknown",
            result.request_id or "unknown",
            size,
        )
        return TranscriptionResponse(
            success=True,
            request_id=result.request_id,
            transcript=result.transcript,
            detected_language_code=result.detected_language_code,
            model=result.model,
            processing_time=result.processing_time,
            end_to_end_latency=result.end_to_end_latency,
        )
    finally:
        await audio.close()
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


@app.post(
    "/api/v1/emergency/analyze",
    response_model=EmergencyAnalysisResponse,
    status_code=status.HTTP_200_OK,
    tags=["emergency"],
    summary="Analyze transcript for emergency indicators",
    description=(
        "Applies deterministic rule-based detection to identify potential "
        "cardiac-respiratory emergency indicators. Requires both unresponsive "
        "and abnormal breathing indicators within the latest three caller "
        "utterances. All results require operator confirmation. This endpoint "
        "does not use LLMs or probabilistic models."
    ),
    responses={
        200: {
            "description": "Emergency analysis completed",
            "content": {
                "application/json": {
                    "example": {
                        "status": "potential_emergency",
                        "risk_category": "cardiac_respiratory",
                        "explanation": "Potential cardiac-respiratory emergency detected...",
                        "matched_indicators": [
                            {
                                "phrase": "unconscious",
                                "category": "unresponsive",
                                "utterance_index": 0,
                                "utterance_text": "He is unconscious",
                                "speaker": "caller",
                            }
                        ],
                        "contradictory_evidence": [],
                        "rule_identifiers": ["RULE_001"],
                        "requires_operator_confirmation": True,
                        "uncertainty_notes": [],
                        "detector_version": "1.0.0",
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
)
def analyze_emergency(request: EmergencyAnalysisRequest) -> EmergencyAnalysisResponse:
    """Analyze transcript utterances for emergency indicators.

    This endpoint applies explainable deterministic rules to detect potential
    emergencies. It does not make medical diagnoses or authorize dispatch.
    All emergency indicators require human operator review and confirmation.
    """
    detector = EmergencyDetector()

    # Convert request utterances to detector format
    utterances = [
        Utterance(
            text=u.text,
            speaker=u.speaker,
            utterance_index=u.utterance_index,
            utterance_id=u.utterance_id or str(__import__('uuid').uuid4()),
            timestamp=u.timestamp,
            language=u.language,
            confidence=u.confidence,
            source=u.source,
        )
        for u in request.utterances
    ]

    # Run detection
    result = detector.analyze(utterances)

    # Convert to response format
    return EmergencyAnalysisResponse(
        status=result.status.value,
        risk_category=result.risk_category.value,
        explanation=result.explanation,
        matched_indicators=[
            MatchedIndicatorResponse(
                phrase=m.phrase,
                category=m.category,
                utterance_index=m.utterance_index,
                utterance_id=m.utterance_id,
                utterance_text=m.utterance_text,
                speaker=m.speaker,
            )
            for m in result.matched_indicators
        ],
        contradictory_evidence=result.contradictory_evidence,
        rule_identifiers=result.rule_identifiers,
        requires_operator_confirmation=result.requires_operator_confirmation,
        uncertainty_notes=result.uncertainty_notes,
        detector_version=result.detector_version,
    )


# TTS endpoint
from backend.app.services.timbre_client import (
    TimbreClient,
    TimbreAPIError,
    TimbreConfigurationError,
    TimbreNetworkError,
    TimbreValidationError,
)
from backend.app.schemas import TTSRequest, TTSPromptsResponse
from fastapi.responses import Response

# Synthesised prompts are fixed text, so cache them in memory: replaying a
# CPR instruction must not wait on the network or spend credits again.
_PROMPT_CACHE: dict[tuple[str, str | None, float], tuple[bytes, str]] = {}
_PROMPT_CACHE_LIMIT = 32


@app.post(
    "/api/v1/tts/synthesize-prompt",
    responses={
        200: {"content": {"audio/wav": {}}, "description": "WAV audio file"},
        400: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    tags=["tts"],
)
async def synthesize_emergency_prompt(request: TTSRequest) -> Response:
    """Synthesize a predefined emergency coaching prompt.

    Only predefined, reviewed emergency prompts are allowed. This prevents
    unrestricted medical instruction generation. Prompts are returned as
    WAV audio for operator-triggered playback, and cached after the first call.
    """

    cache_key = (request.prompt_id, request.voice, round(request.speed, 2))
    cached = _PROMPT_CACHE.get(cache_key)
    if cached is not None:
        audio, media_type = cached
        return Response(content=audio, media_type=media_type, headers={"X-Naadi-Cache": "hit"})

    if not quota.try_consume("tts"):
        return daily_limit_response("tts")

    try:
        client = TimbreClient()
        result = await run_in_threadpool(
            client.synthesize_prompt,
            prompt_id=request.prompt_id,
            voice=request.voice,
            speed=request.speed,
        )
    except TimbreConfigurationError as exc:
        return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "TTS_NOT_CONFIGURED", str(exc))
    except TimbreValidationError as exc:
        return _error_response(status.HTTP_400_BAD_REQUEST, "INVALID_REQUEST", str(exc))
    except TimbreAPIError as exc:
        return _error_response(_upstream_status(exc.status_code), exc.error_code, exc.message)
    except TimbreNetworkError as exc:
        return _error_response(status.HTTP_502_BAD_GATEWAY, "TTS_NETWORK_ERROR", str(exc))

    if len(_PROMPT_CACHE) >= _PROMPT_CACHE_LIMIT:
        _PROMPT_CACHE.pop(next(iter(_PROMPT_CACHE)))
    _PROMPT_CACHE[cache_key] = (result.audio_bytes, result.content_type)
    return Response(
        content=result.audio_bytes,
        media_type=result.content_type,
        headers={"X-Naadi-Cache": "miss"},
    )


@app.get(
    "/api/v1/tts/prompts",
    response_model=TTSPromptsResponse,
    tags=["tts"],
)
async def list_emergency_prompts() -> TTSPromptsResponse:
    """List all available predefined emergency coaching prompts.
    
    Returns metadata for each prompt including language and description.
    Use these prompt_ids with the synthesize-prompt endpoint.
    """
    
    client = TimbreClient()
    prompts = client.list_emergency_prompts()
    
    return TTSPromptsResponse(
        prompts=prompts,
        model="timbre-v3.0",
    )


# ---------- Built frontend (production) ----------
# Registered last so every API route above takes precedence.
if _STATIC_DIR is not None:
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _STATIC_ROOT = _STATIC_DIR.resolve()
    app.mount("/assets", StaticFiles(directory=_STATIC_ROOT / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    def frontend(full_path: str) -> FileResponse | JSONResponse:
        """Serve built files, and index.html for client-side routes like /privacy."""

        if full_path.startswith("api/"):
            return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "No such API endpoint.")
        candidate = (_STATIC_ROOT / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_STATIC_ROOT):
            return FileResponse(candidate)
        # index.html must not be cached, so a new deploy shows up on reload.
        return FileResponse(_STATIC_ROOT / "index.html", headers={"Cache-Control": "no-cache"})
