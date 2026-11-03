"""Unit tests for the Prisma REST client using HTTPX MockTransport."""

from pathlib import Path
from typing import Any

import httpx
import pytest

from backend.app.config import Settings
from backend.app.services.prisma_client import (
    AudioValidationError,
    PrismaAPIError,
    PrismaClient,
    PrismaConfigurationError,
    PrismaNetworkError,
    TranscriptionResult,
    validate_audio_file,
)


def settings(**overrides: Any) -> Settings:
    values = {
        "GNANI_API_KEY": "test-key",
        "GNANI_BASE_URL": "https://api.example.test",
        "GNANI_TIMEOUT_SECONDS": 2,
    }
    values.update(overrides)
    return Settings(**values)


def create_wav(path: Path, *, seconds: float = 1.0) -> None:
    import wave

    frame_rate = 16_000
    frames = int(frame_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(b"\x00\x00" * frames)


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.wav"
    create_wav(path)
    return path


def build_client(handler: Any, **config: Any) -> tuple[PrismaClient, httpx.MockTransport]:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return PrismaClient(settings(**config), http_client=client), transport


def test_successful_transcription_sends_documented_request(audio_file: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://api.example.test/stt/v3"
        assert request.headers["X-API-Key-ID"] == "test-key"
        body = request.content
        assert b'name="model"' in body
        assert b"prisma-v3.0" in body
        assert b'name="language_code"' in body
        assert b"kn-IN,en-IN" in body
        assert b'name="format"' in body
        assert b"codemix" in body
        assert b'name="audio_file"' in body
        return httpx.Response(
            200,
            json={
                "success": True,
                "request_id": "req-test-123",
                "transcript": "ನನಗೆ chest pain ಇದೆ",
                "model": "prisma-v3.0",
                "detected_language_code": "kn-IN",
                "processing_time": 0.42,
                "end_to_end_latency": 0.55,
            },
        )

    client, _ = build_client(handler, **{"GNANI_API_KEY": "test-key"})
    result = client.transcribe(audio_file)

    assert isinstance(result, TranscriptionResult)
    assert result.transcript == "ನನಗೆ chest pain ಇದೆ"
    assert result.detected_language_code == "kn-IN"
    assert result.request_id == "req-test-123"
    assert result.raw_response["model"] == "prisma-v3.0"


def test_missing_api_key_is_rejected_before_request(audio_file: Path) -> None:
    client = PrismaClient(settings(GNANI_API_KEY=None))
    with pytest.raises(PrismaConfigurationError, match="GNANI_API_KEY"):
        client.transcribe(audio_file)


def test_missing_audio_file_is_rejected() -> None:
    client = PrismaClient(settings())
    with pytest.raises(AudioValidationError, match="does not exist"):
        client.transcribe(Path("missing.wav"))


def test_invalid_extension_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "recording.txt"
    path.write_bytes(b"not audio")
    with pytest.raises(AudioValidationError, match="Unsupported audio extension"):
        validate_audio_file(path)


def test_empty_audio_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "empty.wav"
    path.touch()
    with pytest.raises(AudioValidationError, match="empty"):
        validate_audio_file(path)


def test_wav_longer_than_rest_limit_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "long.wav"
    create_wav(path, seconds=30.1)
    with pytest.raises(AudioValidationError, match="at most 30s"):
        validate_audio_file(path)


@pytest.mark.parametrize(
    ("status", "payload", "expected_code"),
    [
        (401, {"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized"}}, "INVALID_API_KEY"),
        (402, {"detail": {"message": "Insufficient credit"}}, "INSUFFICIENT_CREDIT"),
        (403, {"detail": {"error_code": "SCOPE_NOT_ALLOWED", "message": "STT not allowed"}}, "SCOPE_NOT_ALLOWED"),
        (429, {"detail": {"error_code": "RATE_LIMITED", "message": "Try later"}}, "RATE_LIMITED"),
        (500, {"success": False, "error": {"type": "TRANSCRIPTION_FAILED", "message": "Failed"}}, "TRANSCRIPTION_FAILED"),
    ],
)
def test_documented_http_errors(
    audio_file: Path, status: int, payload: dict[str, Any], expected_code: str
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    client, _ = build_client(handler)
    with pytest.raises(PrismaAPIError) as error:
        client.transcribe(audio_file)
    assert error.value.status_code == status
    assert error.value.error_code == expected_code
    assert "test-key" not in str(error.value)


def test_timeout_is_reported_without_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client, _ = build_client(handler)
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        audio = Path(directory) / "sample.wav"
        create_wav(audio)
        with pytest.raises(PrismaNetworkError, match="timed out"):
            client.transcribe(audio)


def test_malformed_api_response_is_rejected(audio_file: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "model": "prisma-v3.0"})

    client, _ = build_client(handler)
    with pytest.raises(PrismaAPIError, match="did not contain a transcript"):
        client.transcribe(audio_file)
