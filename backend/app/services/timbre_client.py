"""HTTPX client for the documented Gnani Timbre TTS REST API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.config import Settings, get_settings


# Predefined emergency coaching prompts (medically reviewed placeholders)
# In production, these should be reviewed by emergency medical professionals
EMERGENCY_PROMPTS = {
    "start_cpr_kannada": {
        "text": "ಎದೆಯ ಮೇಲೆ ಕೈ ಇರಿಸಿ. ಗಟ್ಟಿಯಾಗಿ ಮತ್ತು ವೇಗವಾಗಿ ಒತ್ತಿರಿ. ನಿಮಗೆ ಸಾಧ್ಯವಿರುವವರೆಗೆ ಮುಂದುವರಿಸಿ.",  # Place hands on chest. Push hard and fast. Continue as long as you can.
        "language": "kn-IN",
        "description": "Start CPR instructions in Kannada",
    },
    "start_cpr_hindi": {
        "text": "छाती पर हाथ रखें। जोर से और तेज़ी से दबाएं। जब तक हो सके जारी रखें।",  # Place hands on chest. Push hard and fast. Continue as long as possible.
        "language": "hi-IN",
        "description": "Start CPR instructions in Hindi",
    },
    "start_cpr_english": {
        "text": "Place your hands on the chest. Push hard and fast. Continue as long as you can.",
        "language": "en-IN",
        "description": "Start CPR instructions in English",
    },
    "check_breathing_kannada": {
        "text": "ಉಸಿರಾಟವನ್ನು ಪರಿಶೀಲಿಸಿ. ಎದೆ ಏರುತ್ತಿದೆಯೇ ಎಂದು ನೋಡಿ.",  # Check breathing. See if chest is rising.
        "language": "kn-IN",
        "description": "Check breathing in Kannada",
    },
    "check_breathing_hindi": {
        "text": "सांस की जांच करें। देखें कि छाती ऊपर उठ रही है या नहीं।",  # Check breathing. See if chest is rising.
        "language": "hi-IN",
        "description": "Check breathing in Hindi",
    },
    "check_breathing_english": {
        "text": "Check for breathing. Look to see if the chest is rising.",
        "language": "en-IN",
        "description": "Check breathing in English",
    },
}


class TimbreClientError(Exception):
    """Base class for safe, user-facing Timbre client failures."""


class TimbreConfigurationError(TimbreClientError):
    """Raised when required local configuration is absent or invalid."""


class TimbreValidationError(TimbreClientError):
    """Raised before a request when input validation fails."""


class TimbreAPIError(TimbreClientError):
    """Raised for an HTTP/API response that cannot produce audio."""

    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"Gnani Timbre error ({status_code}, {error_code}): {message}")


class TimbreNetworkError(TimbreClientError):
    """Raised when the request cannot reach Gnani or exceeds its timeout."""


@dataclass(frozen=True)
class TTSResult:
    """Normalized successful TTS response with audio bytes."""

    audio_bytes: bytes
    content_type: str
    audio_duration_estimate: float | None
    raw_response_headers: dict[str, Any]


def _safe_message(value: Any, api_key: str) -> str:
    """Convert an API message to text without ever echoing a configured key."""

    message = str(value)[:500]
    return message.replace(api_key, "[redacted]")


def _api_error_from_response(response: httpx.Response, api_key: str) -> TimbreAPIError:
    """Build a stable error from documented TTS response shapes."""

    try:
        body = response.json()
    except ValueError:
        body = {}

    error_code = "HTTP_ERROR"
    message = response.reason_phrase or "The text-to-speech request failed."

    # TTS uses flat error body: {"success": false, "message": "...", "status_code": ...}
    if isinstance(body, dict):
        if body.get("success") is False and "message" in body:
            message = body["message"]
            error_code = "TTS_ERROR"
        # Gateway errors use nested detail
        elif "detail" in body and isinstance(body["detail"], dict):
            detail = body["detail"]
            error_code = str(detail.get("error_code") or error_code)
            message = detail.get("message") or message

    # Map HTTP status codes to error codes
    if error_code in ("HTTP_ERROR", "TTS_ERROR"):
        error_code = {
            400: "INVALID_REQUEST",
            401: "AUTHENTICATION_FAILED",
            402: "INSUFFICIENT_CREDIT",
            403: "SCOPE_NOT_ALLOWED",
            429: "RATE_LIMITED",
            500: "SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }.get(response.status_code, error_code)

    safe_msg = _safe_message(message, api_key)
    return TimbreAPIError(response.status_code, error_code, safe_msg)


class TimbreClient:
    """Reusable synchronous client for Timbre v3.0 TTS REST inference."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client
        # Use Timbre v3.0 for multilingual support
        self.model = "timbre-v3.0"
        # Default voices for each language (warm, empathetic for emergency contexts)
        self.default_voices = {
            "kn-IN": "Chetana",  # Warm, empathetic - suitable for emergency guidance
            "hi-IN": "Kalpana",  # Empathetic, composed - suitable for customer care
            "en-IN": "Shivani",  # Warm, patient - suitable for support
            "auto": "Shivani",   # Default fallback
        }

    def synthesize_prompt(
        self,
        prompt_id: str,
        *,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize a predefined emergency coaching prompt.
        
        Args:
            prompt_id: ID from EMERGENCY_PROMPTS dictionary
            voice: Optional voice override (defaults to language-appropriate voice)
            speed: Playback speed (0.85-1.15)
            
        Returns:
            TTSResult with audio bytes
            
        Raises:
            TimbreValidationError: If prompt_id is invalid
            TimbreConfigurationError: If API key is missing
            TimbreAPIError: If API returns an error
            TimbreNetworkError: If request fails
        """
        
        if prompt_id not in EMERGENCY_PROMPTS:
            available = ", ".join(sorted(EMERGENCY_PROMPTS.keys()))
            raise TimbreValidationError(
                f"Unknown prompt_id '{prompt_id}'. Available: {available}"
            )
        
        prompt = EMERGENCY_PROMPTS[prompt_id]
        selected_voice = voice or self.default_voices.get(prompt["language"], "Shivani")
        
        return self.synthesize(
            text=prompt["text"],
            language=prompt["language"],
            voice=selected_voice,
            speed=speed,
        )

    def synthesize(
        self,
        text: str,
        language: str,
        *,
        voice: str | None = None,
        speed: float = 1.0,
        sample_rate: int = 48000,
    ) -> TTSResult:
        """Synthesize speech from text using Timbre v3.0.
        
        Args:
            text: Text to synthesize (max length enforced by API)
            language: Language code (kn-IN, hi-IN, en-IN, or auto)
            voice: Voice name (defaults to language-appropriate voice)
            speed: Playback speed multiplier (0.85-1.15)
            sample_rate: Output sample rate (8000-48000 Hz)
            
        Returns:
            TTSResult with WAV audio bytes
            
        Raises:
            TimbreConfigurationError: If API key is missing
            TimbreValidationError: If input parameters are invalid
            TimbreAPIError: If API returns an error
            TimbreNetworkError: If request fails
        """
        
        if not self.settings.has_gnani_api_key:
            raise TimbreConfigurationError(
                "GNANI_API_KEY is not configured. Copy .env.example to .env "
                "and set the key locally."
            )
        
        # Validate inputs
        if not text or not text.strip():
            raise TimbreValidationError("Text cannot be empty.")
        
        if len(text) > 5000:
            raise TimbreValidationError(
                f"Text is too long ({len(text)} chars). Maximum: 5000 characters."
            )
        
        if speed < 0.85 or speed > 1.15:
            raise TimbreValidationError(
                f"Speed {speed} is out of range. Allowed: 0.85-1.15"
            )
        
        if sample_rate not in (8000, 16000, 22050, 24000, 44100, 48000):
            raise TimbreValidationError(
                f"Sample rate {sample_rate} is invalid. "
                "Allowed: 8000, 16000, 22050, 24000, 44100, 48000"
            )
        
        # Select voice
        selected_voice = voice or self.default_voices.get(language, "Shivani")
        
        # Build request payload
        payload = {
            "text": text.strip(),
            "voice": selected_voice,
            "model": self.model,
            "language": language,
            "speed": speed,
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key-ID": self.settings.gnani_api_key or "",
        }
        
        # Make request
        tts_url = "https://api.vachana.ai/api/v1/tts/inference"
        
        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    tts_url,
                    json=payload,
                    headers=headers,
                    timeout=self.settings.gnani_timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.settings.gnani_timeout_seconds) as client:
                    response = client.post(
                        tts_url,
                        json=payload,
                        headers=headers,
                    )
        except httpx.TimeoutException as exc:
            raise TimbreNetworkError(
                "The Gnani Timbre request timed out. Check connectivity and try again."
            ) from exc
        except httpx.RequestError as exc:
            raise TimbreNetworkError(
                "The Gnani Timbre request could not reach the service. Check connectivity."
            ) from exc
        
        # Check for errors
        if response.status_code != 200:
            raise _api_error_from_response(response, self.settings.gnani_api_key or "")
        
        # Successful response is binary audio
        content_type = response.headers.get("content-type", "audio/wav")
        
        # Validate we received audio, not JSON error
        if "application/json" in content_type.lower():
            try:
                error_body = response.json()
                if isinstance(error_body, dict) and error_body.get("success") is False:
                    message = error_body.get("message", "TTS failed")
                    raise TimbreAPIError(200, "TTS_FAILED", message)
            except ValueError:
                pass
            raise TimbreAPIError(
                200,
                "UNEXPECTED_RESPONSE",
                "Expected audio but received JSON response."
            )
        
        audio_bytes = response.content
        
        if len(audio_bytes) == 0:
            raise TimbreAPIError(200, "EMPTY_AUDIO", "Received empty audio response.")
        
        # Estimate duration (for WAV: bytes / sample_rate / channels / sample_width)
        # Rough estimate: 48000 Hz * 1 channel * 2 bytes = 96000 bytes/sec
        duration_estimate = None
        if sample_rate and audio_bytes:
            bytes_per_second = sample_rate * 1 * 2  # mono, 16-bit
            # Subtract WAV header (typically 44 bytes)
            audio_data_size = max(0, len(audio_bytes) - 44)
            if bytes_per_second > 0:
                duration_estimate = audio_data_size / bytes_per_second
        
        return TTSResult(
            audio_bytes=audio_bytes,
            content_type=content_type,
            audio_duration_estimate=duration_estimate,
            raw_response_headers=dict(response.headers),
        )
    
    def list_emergency_prompts(self) -> dict[str, dict[str, str]]:
        """List all available predefined emergency prompts.
        
        Returns:
            Dictionary mapping prompt_id to prompt metadata
        """
        return {
            prompt_id: {
                "language": prompt["language"],
                "description": prompt["description"],
            }
            for prompt_id, prompt in EMERGENCY_PROMPTS.items()
        }
