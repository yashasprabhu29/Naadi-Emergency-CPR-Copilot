"""FastAPI endpoint tests with a mocked Prisma transport."""

from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.config import Settings
from backend.app.services.prisma_client import PrismaClient


def wav_bytes(*, seconds: float = 1.0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\x00\x00" * int(16_000 * seconds))
    return buffer.getvalue()


def fake_prisma(handler: Any, *, api_key: str | None = "test-key") -> PrismaClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    settings = Settings(
        GNANI_API_KEY=api_key,
        GNANI_BASE_URL="https://api.example.test",
        GNANI_TIMEOUT_SECONDS=2,
    )
    return PrismaClient(settings, http_client=http_client)


@pytest.fixture
def api_client() -> TestClient:
    client = TestClient(main.app)
    yield client
    main.app.dependency_overrides.clear()


def successful_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/stt/v3"
    assert request.headers["X-API-Key-ID"] == "test-key"
    return httpx.Response(
        200,
        json={
            "success": True,
            "request_id": "req-api-123",
            "transcript": "ನನಗೆ chest pain ಇದೆ",
            "detected_language_code": "kn-IN",
            "model": "prisma-v3.0",
            "processing_time": 0.42,
            "end_to_end_latency": 0.55,
        },
    )


def test_successful_upload_returns_structured_transcription(api_client: TestClient) -> None:
    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(
        successful_handler
    )

    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "request_id": "req-api-123",
        "transcript": "ನನಗೆ chest pain ಇದೆ",
        "detected_language_code": "kn-IN",
        "model": "prisma-v3.0",
        "processing_time": 0.42,
        "end_to_end_latency": 0.55,
    }


def test_missing_upload_returns_safe_error(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/transcriptions")

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": {
            "code": "MISSING_AUDIO",
            "message": "Upload one audio file using the 'audio' form field.",
        },
    }


def test_empty_upload_returns_safe_error(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_AUDIO"


def test_invalid_extension_returns_safe_error(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.txt", b"audio", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_AUDIO_EXTENSION"


def test_invalid_mime_type_returns_415(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_oversized_upload_returns_413(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "max_upload_size_bytes", 10)

    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", b"01234567890", "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "UPLOAD_TOO_LARGE"


def test_invalid_audio_returns_400(api_client: TestClient) -> None:
    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(
        successful_handler
    )

    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", b"not a wav file", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AUDIO"


def test_missing_api_key_returns_503(api_client: TestClient) -> None:
    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(
        successful_handler, api_key=None
    )

    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GNANI_NOT_CONFIGURED"
    assert "test-key" not in response.text


@pytest.mark.parametrize(
    ("status", "payload", "expected_status", "expected_code"),
    [
        (401, {"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized"}}, 401, "INVALID_API_KEY"),
        (402, {"detail": {"message": "Insufficient credit"}}, 402, "INSUFFICIENT_CREDIT"),
        (403, {"detail": {"error_code": "SCOPE_NOT_ALLOWED", "message": "STT not allowed"}}, 403, "SCOPE_NOT_ALLOWED"),
        (429, {"detail": {"error_code": "RATE_LIMITED", "message": "Try later"}}, 429, "RATE_LIMITED"),
        (500, {"error": {"type": "TRANSCRIPTION_FAILED", "message": "Failed"}}, 500, "TRANSCRIPTION_FAILED"),
    ],
)
def test_upstream_http_errors(
    api_client: TestClient,
    status: int,
    payload: dict[str, Any],
    expected_status: int,
    expected_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(handler)
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code


def test_timeout_returns_504(api_client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(handler)
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


def test_network_failure_returns_502(api_client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unavailable", request=request)

    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(handler)
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_NETWORK_ERROR"


def test_malformed_upstream_response_returns_502(api_client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": True, "model": "prisma-v3.0"})

    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(handler)
    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "MALFORMED_RESPONSE"


def test_health_endpoints_do_not_call_prisma(api_client: TestClient) -> None:
    root = api_client.get("/")
    health = api_client.get("/health")
    api_health = api_client.get("/api/v1/health")

    assert root.status_code == 200
    assert health.status_code == 200
    assert api_health.status_code == 200
    assert api_health.json()["status"] == "ok"
    assert api_health.json()["gnani_api_key_configured"] is False


def test_local_frontend_cors_is_explicitly_allowed(api_client: TestClient) -> None:
    allowed = api_client.options(
        "/api/v1/transcriptions",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    disallowed = api_client.get(
        "/api/v1/health",
        headers={"Origin": "https://untrusted.example"},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in disallowed.headers


def test_openapi_documents_upload_endpoint_and_constraints(api_client: TestClient) -> None:
    response = api_client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    operation = document["paths"]["/api/v1/transcriptions"]["post"]
    assert "multipart/form-data" in operation["requestBody"]["content"]
    assert "30 seconds" in operation["description"]
    schema_ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = schema_ref.rsplit("/", 1)[-1]
    upload_schema = document["components"]["schemas"][schema_name]
    assert "audio" in upload_schema["properties"]
    assert "Supported extensions" in upload_schema["properties"]["audio"]["description"]
    assert "413" in operation["responses"]
    assert "503" in operation["responses"]


def test_upload_temporary_file_is_cleaned_up(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    main.app.dependency_overrides[main.get_prisma_client] = lambda: fake_prisma(
        successful_handler
    )

    response = api_client.post(
        "/api/v1/transcriptions",
        files={"audio": ("call.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 200
    assert list(tmp_path.glob("naadi-upload-*")) == []
