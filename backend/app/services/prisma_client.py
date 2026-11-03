"""HTTPX client for the documented Gnani Prisma REST API."""

from __future__ import annotations

import mimetypes
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from backend.app.config import Settings, get_settings


SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"})
MAX_REST_DURATION_SECONDS = 30.0


class PrismaClientError(Exception):
    """Base class for safe, user-facing Prisma client failures."""


class PrismaConfigurationError(PrismaClientError):
    """Raised when required local configuration is absent or invalid."""


class AudioValidationError(PrismaClientError):
    """Raised before a request when the local audio file is invalid."""


class PrismaAPIError(PrismaClientError):
    """Raised for an HTTP/API response that cannot produce a transcript."""

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"Gnani Prisma error ({status_code}, {error_code}): {message}")


class PrismaNetworkError(PrismaClientError):
    """Raised when the request cannot reach Gnani or exceeds its timeout."""


@dataclass(frozen=True)
class TranscriptionResult:
    """Normalized successful response plus the original safe JSON body."""

    transcript: str
    request_id: str | None
    model: str | None
    detected_language_code: str | None
    processing_time: float | None
    end_to_end_latency: float | None
    truncated: bool
    raw_response: dict[str, Any]


def _safe_message(value: Any) -> str:
    """Convert an API message to text without ever echoing a configured key."""

    return str(value)[:500]


def _api_error_from_response(response: httpx.Response, api_key: str) -> PrismaAPIError:
    """Build a stable error from documented and gateway response shapes."""

    try:
        body = response.json()
    except ValueError:
        body = {}

    error_code = "HTTP_ERROR"
    message = response.reason_phrase or "The transcription request failed."

    if isinstance(body, dict):
        detail = body.get("detail")
        error = body.get("error")

        if isinstance(detail, dict):
            error_code = str(detail.get("error_code") or detail.get("type") or error_code)
            message = detail.get("message") or message
        elif isinstance(error, dict):
            error_code = str(error.get("type") or error.get("code") or error_code)
            message = error.get("message") or message
        elif isinstance(error, str):
            error_code = str(body.get("code") or error_code)
            message = body.get("message") or error
        elif body.get("message"):
            message = body["message"]

    if error_code == "HTTP_ERROR":
        error_code = {
            401: "AUTHENTICATION_FAILED",
            402: "INSUFFICIENT_CREDIT",
            403: "PERMISSION_DENIED",
            429: "RATE_LIMITED",
        }.get(response.status_code, error_code)

    # Never include the credential in an exception, even if an upstream error
    # unexpectedly reflects request data.
    safe_message = _safe_message(message).replace(api_key, "[redacted]")
    return PrismaAPIError(response.status_code, error_code, safe_message)


def validate_audio_file(audio_path: Path) -> float | None:
    """Validate extension, existence, size and inspectable WAV duration.

    Returns WAV duration in seconds when available. Compressed formats return
    ``None`` because the standard library cannot reliably inspect their length.
    Gnani enforces the documented 30-second limit for those formats.
    """

    if not audio_path.exists():
        raise AudioValidationError(f"Audio file does not exist: {audio_path}")
    if not audio_path.is_file():
        raise AudioValidationError(f"Audio path is not a regular file: {audio_path}")
    if audio_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise AudioValidationError(
            f"Unsupported audio extension '{audio_path.suffix or '<none>'}'. "
            f"Supported extensions: {supported}"
        )
    if audio_path.stat().st_size == 0:
        raise AudioValidationError("Audio file is empty.")

    if audio_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
                if frame_rate <= 0:
                    raise AudioValidationError("WAV file has an invalid sample rate.")
                duration = frame_count / frame_rate
        except (wave.Error, EOFError) as exc:
            raise AudioValidationError(f"WAV file could not be parsed: {exc}") from exc
        if duration > MAX_REST_DURATION_SECONDS:
            raise AudioValidationError(
                f"WAV duration is {duration:.2f}s; Prisma REST accepts at most "
                f"{MAX_REST_DURATION_SECONDS:.0f}s per request."
            )
        return duration

    return None


class PrismaClient:
    """Reusable synchronous client for Prisma v3.0 REST transcription."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        language_code: str | None = None,
        format: str | None = None,
    ) -> TranscriptionResult:
        """Submit a staged recording to the official Prisma REST endpoint."""

        if not self.settings.has_gnani_api_key:
            raise PrismaConfigurationError(
                "GNANI_API_KEY is not configured. Copy .env.example to .env "
                "and set the key locally."
            )

        path = Path(audio_path)
        validate_audio_file(path)

        request_data = {
            "model": self.settings.gnani_model,
            "language_code": language_code or self.settings.gnani_language_code,
            "format": format or self.settings.gnani_format,
        }
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        headers = {"X-API-Key-ID": self.settings.gnani_api_key or ""}

        try:
            with path.open("rb") as audio_file:
                files = {"audio_file": (path.name, audio_file, content_type)}
                if self._http_client is not None:
                    response = self._http_client.post(
                        self.settings.gnani_api_url,
                        headers=headers,
                        data=request_data,
                        files=files,
                        timeout=self.settings.gnani_timeout_seconds,
                    )
                else:
                    with httpx.Client(timeout=self.settings.gnani_timeout_seconds) as client:
                        response = client.post(
                            self.settings.gnani_api_url,
                            headers=headers,
                            data=request_data,
                            files=files,
                        )
        except httpx.TimeoutException as exc:
            raise PrismaNetworkError(
                "The Gnani Prisma request timed out. Check connectivity and try again."
            ) from exc
        except httpx.RequestError as exc:
            raise PrismaNetworkError(
                "The Gnani Prisma request could not reach the service. Check connectivity."
            ) from exc

        if response.status_code != 200:
            raise _api_error_from_response(response, self.settings.gnani_api_key or "")

        try:
            body = response.json()
        except ValueError as exc:
            raise PrismaAPIError(200, "MALFORMED_RESPONSE", "Gnani returned invalid JSON.") from exc

        if not isinstance(body, dict):
            raise PrismaAPIError(200, "MALFORMED_RESPONSE", "Gnani returned an invalid response object.")
        if body.get("success") is False:
            raise PrismaAPIError(200, "API_REPORTED_FAILURE", "Gnani reported transcription failure.")
        transcript = body.get("transcript")
        if not isinstance(transcript, str):
            raise PrismaAPIError(200, "MALFORMED_RESPONSE", "Gnani response did not contain a transcript.")

        return TranscriptionResult(
            transcript=transcript,
            request_id=body.get("request_id") if isinstance(body.get("request_id"), str) else None,
            model=body.get("model") if isinstance(body.get("model"), str) else None,
            detected_language_code=(
                body.get("detected_language_code")
                if isinstance(body.get("detected_language_code"), str)
                else None
            ),
            processing_time=(
                float(body["processing_time"])
                if isinstance(body.get("processing_time"), (int, float))
                else None
            ),
            end_to_end_latency=(
                float(body["end_to_end_latency"])
                if isinstance(body.get("end_to_end_latency"), (int, float))
                else None
            ),
            truncated=body.get("truncated") is True,
            raw_response=body,
        )
