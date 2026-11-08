"""Tests for the Timbre TTS client."""

import pytest
from unittest.mock import Mock, patch
import httpx

from backend.app.services.timbre_client import (
    TimbreClient,
    TimbreAPIError,
    TimbreConfigurationError,
    TimbreNetworkError,
    TimbreValidationError,
    EMERGENCY_PROMPTS,
)


@pytest.fixture
def mock_settings():
    """Mock settings with API key."""
    settings = Mock()
    settings.gnani_api_key = "test-api-key"
    settings.has_gnani_api_key = True
    settings.gnani_timeout_seconds = 60.0
    return settings


@pytest.fixture
def client_with_settings(mock_settings):
    """Timbre client with mocked settings."""
    return TimbreClient(settings=mock_settings)


def test_list_emergency_prompts(client_with_settings):
    """Test listing available emergency prompts."""
    prompts = client_with_settings.list_emergency_prompts()
    
    assert isinstance(prompts, dict)
    assert len(prompts) > 0
    assert "start_cpr_kannada" in prompts
    assert "check_breathing_hindi" in prompts
    
    # Verify structure
    for prompt_id, metadata in prompts.items():
        assert "language" in metadata
        assert "description" in metadata


def test_synthesize_prompt_invalid_id(client_with_settings):
    """Test synthesize with invalid prompt_id."""
    with pytest.raises(TimbreValidationError, match="Unknown prompt_id"):
        client_with_settings.synthesize_prompt("invalid_prompt_id")


def test_synthesize_empty_text_rejected(client_with_settings):
    """Test that empty text is rejected."""
    with pytest.raises(TimbreValidationError, match="Text cannot be empty"):
        client_with_settings.synthesize(
            text="",
            language="en-IN",
        )


def test_synthesize_text_too_long_rejected(client_with_settings):
    """Test that overly long text is rejected."""
    long_text = "a" * 5001
    with pytest.raises(TimbreValidationError, match="Text is too long"):
        client_with_settings.synthesize(
            text=long_text,
            language="en-IN",
        )


def test_synthesize_invalid_speed_rejected(client_with_settings):
    """Test that invalid speed is rejected."""
    with pytest.raises(TimbreValidationError, match="Speed .* is out of range"):
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
            speed=2.0,  # Out of 0.85-1.15 range
        )


def test_synthesize_invalid_sample_rate_rejected(client_with_settings):
    """Test that invalid sample rate is rejected."""
    with pytest.raises(TimbreValidationError, match="Sample rate .* is invalid"):
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
            sample_rate=12345,
        )


def test_missing_api_key_rejected_before_request():
    """Test that missing API key is caught before making a request."""
    settings = Mock()
    settings.gnani_api_key = None
    settings.has_gnani_api_key = False
    
    client = TimbreClient(settings=settings)
    
    with pytest.raises(TimbreConfigurationError, match="GNANI_API_KEY is not configured"):
        client.synthesize(
            text="test",
            language="en-IN",
        )


@patch("httpx.Client")
def test_synthesize_success(mock_client_class, client_with_settings):
    """Test successful synthesis returns audio bytes."""
    # Mock successful response with WAV audio
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"RIFF" + b"\x00" * 100  # Fake WAV data
    mock_response.headers = {"content-type": "audio/wav"}
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    result = client_with_settings.synthesize(
        text="test text",
        language="en-IN",
    )
    
    assert result.audio_bytes == mock_response.content
    assert result.content_type == "audio/wav"
    assert isinstance(result.audio_duration_estimate, (float, type(None)))


@patch("httpx.Client")
def test_synthesize_400_error(mock_client_class, client_with_settings):
    """Test 400 Bad Request error handling."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.reason_phrase = "Bad Request"
    mock_response.json.return_value = {
        "success": False,
        "message": "Invalid request: Field required at body -> text",
        "status_code": 400,
    }
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreAPIError) as exc_info:
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_REQUEST"


@patch("httpx.Client")
def test_synthesize_401_authentication_failed(mock_client_class, client_with_settings):
    """Test 401 authentication error handling."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.reason_phrase = "Unauthorized"
    mock_response.json.return_value = {
        "detail": {
            "error_code": "INVALID_API_KEY",
            "message": "Unauthorized",
            "status_code": 401,
        }
    }
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreAPIError) as exc_info:
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )
    
    assert exc_info.value.status_code == 401
    assert "INVALID_API_KEY" in exc_info.value.error_code or "AUTHENTICATION" in exc_info.value.error_code


@patch("httpx.Client")
def test_synthesize_429_rate_limited(mock_client_class, client_with_settings):
    """Test 429 rate limit error handling."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.reason_phrase = "Too Many Requests"
    mock_response.json.return_value = {
        "detail": {
            "error_code": "RATE_LIMITED",
            "message": "Only 1 active request is allowed at a time.",
            "status_code": 429,
        }
    }
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreAPIError) as exc_info:
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )
    
    assert exc_info.value.status_code == 429
    assert "RATE_LIMITED" in exc_info.value.error_code


@patch("httpx.Client")
def test_synthesize_timeout(mock_client_class, client_with_settings):
    """Test timeout handling."""
    mock_client = Mock()
    mock_client.post.side_effect = httpx.TimeoutException("Connection timeout")
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreNetworkError, match="timed out"):
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )


@patch("httpx.Client")
def test_synthesize_network_error(mock_client_class, client_with_settings):
    """Test network error handling."""
    mock_client = Mock()
    mock_client.post.side_effect = httpx.RequestError("Connection failed")
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreNetworkError, match="could not reach"):
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )


@patch("httpx.Client")
def test_synthesize_empty_audio_rejected(mock_client_class, client_with_settings):
    """Test that empty audio response is rejected."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b""  # Empty audio
    mock_response.headers = {"content-type": "audio/wav"}
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    with pytest.raises(TimbreAPIError, match="empty audio"):
        client_with_settings.synthesize(
            text="test",
            language="en-IN",
        )


@patch("httpx.Client")
def test_synthesize_prompt_uses_appropriate_voice(mock_client_class, client_with_settings):
    """Test that synthesize_prompt selects language-appropriate voices."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"RIFF" + b"\x00" * 100
    mock_response.headers = {"content-type": "audio/wav"}
    
    mock_client = Mock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_client_class.return_value.__exit__.return_value = None
    
    
    # Test Kannada prompt uses Chetana
    result = client_with_settings.synthesize_prompt("start_cpr_kannada")
    call_args = mock_client.post.call_args
    payload = call_args.kwargs["json"]
    
    assert payload["voice"] == "Chetana"
    assert payload["language"] == "kn-IN"
    assert payload["model"] == "timbre-v3.0"


def test_emergency_prompts_structure():
    """Verify emergency prompts have required structure."""
    for prompt_id, prompt in EMERGENCY_PROMPTS.items():
        assert "text" in prompt
        assert "language" in prompt
        assert "description" in prompt
        assert isinstance(prompt["text"], str)
        assert len(prompt["text"]) > 0
        assert prompt["language"] in ("kn-IN", "hi-IN", "en-IN")
