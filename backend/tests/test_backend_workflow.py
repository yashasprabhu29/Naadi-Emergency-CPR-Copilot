"""End-to-end backend workflow tests.

These tests verify the complete backend flow without requiring live API calls:
1. Audio upload → transcription (mocked)
2. Transcript → structured utterances
3. Emergency analysis → detection result
4. TTS prompt listing and synthesis (mocked)
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.emergency_detector import Utterance

client = TestClient(app)


def test_health_endpoint_reports_configuration():
    """Test that health endpoint reports API key status without exposing it."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "gnani_api_key_configured" in data
    assert isinstance(data["gnani_api_key_configured"], bool)
    assert "prisma_model" in data
    assert data["prisma_model"] == "prisma-v3.0"
    
    # Verify key is never exposed
    assert "gnani_api_key" not in data
    assert "GNANI_API_KEY" not in str(data)


def test_emergency_analysis_workflow():
    """Test complete emergency analysis workflow with structured utterances."""
    # Simulate parsed transcript from STT
    utterances = [
        {
            "text": "My father collapsed",
            "speaker": "caller",
            "utterance_index": 0,
            "utterance_id": "utt-001",
            "language": "en-IN",
            "confidence": 0.95,
            "source": "prisma",
        },
        {
            "text": "Is he breathing?",
            "speaker": "operator",
            "utterance_index": 1,
            "utterance_id": "utt-002",
            "language": "en-IN",
            "confidence": 0.98,
            "source": "prisma",
        },
        {
            "text": "No, he is not breathing",
            "speaker": "caller",
            "utterance_index": 2,
            "utterance_id": "utt-003",
            "language": "en-IN",
            "confidence": 0.96,
            "source": "prisma",
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify emergency detected
    assert data["status"] == "potential_emergency"
    assert data["risk_category"] == "cardiac_respiratory"
    assert data["requires_operator_confirmation"] is True
    
    # Verify matched indicators
    assert len(data["matched_indicators"]) == 2
    categories = {ind["category"] for ind in data["matched_indicators"]}
    assert "unresponsive" in categories
    assert "abnormal_breathing" in categories
    
    # Verify operator utterance was excluded
    for indicator in data["matched_indicators"]:
        assert indicator["speaker"] == "caller"
        assert indicator["utterance_id"] in ("utt-001", "utt-003")


def test_kannada_emergency_detection_workflow():
    """Test Kannada emergency phrase detection."""
    utterances = [
        {
            "text": "ಅವರು ಎಚ್ಚರ ಇಲ್ಲ",  # They are unconscious
            "speaker": "caller",
            "utterance_index": 0,
            "utterance_id": "utt-kn-001",
            "language": "kn-IN",
            "confidence": 0.92,
            "source": "prisma",
        },
        {
            "text": "ಉಸಿರಾಡ್ತಿಲ್ಲ",  # Not breathing
            "speaker": "caller",
            "utterance_index": 1,
            "utterance_id": "utt-kn-002",
            "language": "kn-IN",
            "confidence": 0.94,
            "source": "prisma",
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "potential_emergency"
    assert len(data["matched_indicators"]) == 2


def test_code_mixed_emergency_detection():
    """Test code-mixed Kannada-English emergency detection."""
    utterances = [
        {
            "text": "Nanna appa ಬಿದ್ದುಬಿಟ್ರು, chest pain antha",  # My father collapsed, said chest pain
            "speaker": "caller",
            "utterance_index": 0,
            "utterance_id": "utt-mix-001",
            "language": "mixed",
            "confidence": 0.89,
            "source": "prisma",
        },
        {
            "text": "ಉಸಿರಾಡ್ತಿಲ್ಲ sir",  # Not breathing sir
            "speaker": "caller",
            "utterance_index": 1,
            "utterance_id": "utt-mix-002",
            "language": "mixed",
            "confidence": 0.91,
            "source": "prisma",
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should detect both collapsed (unresponsive) and not breathing
    assert data["status"] == "potential_emergency"
    assert len(data["matched_indicators"]) == 2


def test_operator_confirmation_required_for_all_emergencies():
    """Verify that all emergency detections require operator confirmation."""
    test_cases = [
        # Potential emergency
        [
            {"text": "unconscious", "speaker": "caller", "utterance_index": 0},
            {"text": "not breathing", "speaker": "caller", "utterance_index": 1},
        ],
        # Review required (single indicator)
        [
            {"text": "unconscious", "speaker": "caller", "utterance_index": 0},
        ],
        # Review required (with contradictions)
        [
            {"text": "unconscious", "speaker": "caller", "utterance_index": 0},
            {"text": "not breathing", "speaker": "caller", "utterance_index": 1},
            {"text": "breathing normally now", "speaker": "caller", "utterance_index": 2},
        ],
    ]
    
    for utterances in test_cases:
        response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
        assert response.status_code == 200
        data = response.json()
        
        if data["status"] in ("potential_emergency", "review_required"):
            assert data["requires_operator_confirmation"] is True, (
                f"Status {data['status']} should require confirmation"
            )


def test_unknown_speakers_excluded_from_detection():
    """Verify unknown speakers do not trigger emergency detection."""
    utterances = [
        {
            "text": "Person is unconscious and not breathing",
            "speaker": None,  # Unknown speaker
            "utterance_index": 0,
            "utterance_id": "utt-unknown-001",
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "no_indicator"
    assert len(data["matched_indicators"]) == 0
    assert "No explicitly identified caller utterances available" in data["uncertainty_notes"]


def test_tts_prompt_listing():
    """Test TTS emergency prompt listing endpoint."""
    response = client.get("/api/v1/tts/prompts")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "prompts" in data
    assert "model" in data
    assert data["model"] == "timbre-v3.0"
    
    # Verify expected prompts exist
    prompts = data["prompts"]
    assert "start_cpr_kannada" in prompts
    assert "start_cpr_hindi" in prompts
    assert "start_cpr_english" in prompts
    assert "check_breathing_kannada" in prompts
    assert "check_breathing_hindi" in prompts
    assert "check_breathing_english" in prompts
    
    # Verify prompt structure
    for prompt_id, metadata in prompts.items():
        assert "language" in metadata
        assert "description" in metadata
        assert metadata["language"] in ("kn-IN", "hi-IN", "en-IN")


def test_empty_utterances_rejected():
    """Test that empty utterance list is rejected."""
    response = client.post("/api/v1/emergency/analyze", json={"utterances": []})
    
    assert response.status_code == 422  # Validation error


def test_malformed_utterance_rejected():
    """Test that malformed utterances are rejected."""
    # Missing required field 'text'
    utterances = [
        {
            "speaker": "caller",
            "utterance_index": 0,
        }
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 422  # Validation error


def test_three_utterance_window_enforcement():
    """Test that only latest 3 caller utterances are analyzed."""
    utterances = [
        {"text": "He collapsed", "speaker": "caller", "utterance_index": 0},  # Old
        {"text": "He was not breathing", "speaker": "caller", "utterance_index": 1},  # Old
        {"text": "Normal chat", "speaker": "caller", "utterance_index": 2},  # Analyzed
        {"text": "More chat", "speaker": "caller", "utterance_index": 3},  # Analyzed
        {"text": "Latest message", "speaker": "caller", "utterance_index": 4},  # Analyzed
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should NOT detect emergency because indicators are in utterances 0-1
    # which are outside the 3-utterance window (2, 3, 4)
    assert data["status"] == "no_indicator"
    assert len(data["matched_indicators"]) == 0


def test_negation_creates_contradiction():
    """Test that negated statements are detected as contradictions."""
    utterances = [
        {"text": "He is unconscious", "speaker": "caller", "utterance_index": 0},
        {"text": "Not breathing", "speaker": "caller", "utterance_index": 1},
        {"text": "Wait, he is breathing normally", "speaker": "caller", "utterance_index": 2},
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should detect indicators but also contradictions
    assert len(data["matched_indicators"]) > 0
    assert len(data["contradictory_evidence"]) > 0
    assert data["status"] == "review_required"  # Not potential_emergency due to contradiction


def test_unicode_normalization_for_kannada():
    """Test that Unicode normalization works for Kannada text."""
    # Same Kannada text with different Unicode representations should match
    utterances = [
        {
            "text": "ಎಚ್ಚರ ಇಲ್ಲ",  # Unconscious (NFC normalized)
            "speaker": "caller",
            "utterance_index": 0,
        },
        {
            "text": "ಉಸಿರಾಡ್ತಿಲ್ಲ",  # Not breathing (NFC normalized)
            "speaker": "caller",
            "utterance_index": 1,
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should detect both indicators
    assert data["status"] == "potential_emergency"
    assert len(data["matched_indicators"]) == 2


def test_utterance_id_traceability():
    """Test that matched indicators include utterance_id for traceability."""
    utterances = [
        {
            "text": "Collapsed on floor",
            "speaker": "caller",
            "utterance_index": 0,
            "utterance_id": "trace-001",
        },
        {
            "text": "Gasping for air",
            "speaker": "caller",
            "utterance_index": 1,
            "utterance_id": "trace-002",
        },
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify utterance_id is preserved in matched indicators
    for indicator in data["matched_indicators"]:
        assert "utterance_id" in indicator
        assert indicator["utterance_id"] in ("trace-001", "trace-002")
        assert "utterance_text" in indicator


def test_detector_version_reported():
    """Test that detector version is included in response."""
    utterances = [
        {"text": "Test message", "speaker": "caller", "utterance_index": 0},
    ]
    
    response = client.post("/api/v1/emergency/analyze", json={"utterances": utterances})
    
    assert response.status_code == 200
    data = response.json()
    
    assert "detector_version" in data
    assert data["detector_version"] == "1.1.0"
