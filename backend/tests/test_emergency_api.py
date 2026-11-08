"""API tests for the emergency detection endpoint."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_analyze_emergency_potential_emergency():
    """Test successful emergency indicator detection."""
    payload = {
        "utterances": [
            {"text": "He is unconscious", "speaker": "caller", "utterance_index": 0},
            {"text": "He is not breathing", "speaker": "caller", "utterance_index": 1},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potential_emergency"
    assert data["risk_category"] == "cardiac_respiratory"
    assert data["requires_operator_confirmation"] is True
    assert len(data["matched_indicators"]) == 2
    assert "RULE_001" in data["rule_identifiers"]
    assert data["detector_version"] == "1.1.0"


def test_analyze_emergency_review_required():
    """Test single indicator triggering review."""
    payload = {
        "utterances": [
            {"text": "He is unconscious", "speaker": "caller", "utterance_index": 0},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "review_required"
    assert data["risk_category"] == "uncertain"
    assert data["requires_operator_confirmation"] is True


def test_analyze_emergency_no_indicator():
    """Test no indicators detected."""
    payload = {
        "utterances": [
            {"text": "Everything is fine", "speaker": "caller", "utterance_index": 0},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_indicator"
    assert data["risk_category"] == "none"
    assert data["requires_operator_confirmation"] is False
    assert len(data["matched_indicators"]) == 0


def test_analyze_emergency_with_contradictions():
    """Test detection with contradictory evidence."""
    payload = {
        "utterances": [
            {"text": "He is unconscious", "speaker": "caller", "utterance_index": 0},
            {"text": "Not breathing", "speaker": "caller", "utterance_index": 1},
            {"text": "Wait, he is breathing now", "speaker": "caller", "utterance_index": 2},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "review_required"
    assert len(data["contradictory_evidence"]) > 0
    assert "CONTRADICTION_DETECTED" in data["rule_identifiers"]


def test_analyze_emergency_operator_utterances_excluded():
    """Test that operator utterances are excluded from analysis."""
    payload = {
        "utterances": [
            {"text": "What is the emergency?", "speaker": "operator", "utterance_index": 0},
            {"text": "He is unconscious", "speaker": "caller", "utterance_index": 1},
            {"text": "Can you describe?", "speaker": "operator", "utterance_index": 2},
            {"text": "Not breathing", "speaker": "caller", "utterance_index": 3},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potential_emergency"
    # Only caller utterances should be in matched indicators
    for indicator in data["matched_indicators"]:
        assert indicator["speaker"] == "caller"


def test_analyze_emergency_kannada_detection():
    """Test Kannada phrase detection."""
    payload = {
        "utterances": [
            {"text": "ಎಚ್ಚರ ಇಲ್ಲ", "speaker": "caller", "utterance_index": 0},
            {"text": "ಉಸಿರಾಡ್ತಿಲ್ಲ", "speaker": "caller", "utterance_index": 1},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potential_emergency"


def test_analyze_emergency_hindi_detection():
    """Test Hindi phrase detection."""
    payload = {
        "utterances": [
            {"text": "बेहोश है", "speaker": "caller", "utterance_index": 0},
            {"text": "साँस नहीं", "speaker": "caller", "utterance_index": 1},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potential_emergency"


def test_analyze_emergency_empty_utterances():
    """Test validation error for empty utterances list."""
    payload = {"utterances": []}
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 422  # Validation error


def test_analyze_emergency_missing_text():
    """Test validation error for missing text field."""
    payload = {
        "utterances": [
            {"speaker": "caller", "utterance_index": 0}  # Missing text
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_emergency_empty_text():
    """Test validation error for empty text."""
    payload = {
        "utterances": [
            {"text": "", "speaker": "caller", "utterance_index": 0}
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_emergency_unknown_speaker():
    """Test that unknown speaker utterances are NOT analyzed (excluded from detection)."""
    payload = {
        "utterances": [
            {"text": "He is unconscious", "speaker": None, "utterance_index": 0},
            {"text": "Not breathing", "speaker": None, "utterance_index": 1},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    # Unknown speakers should NOT trigger detection
    assert data["status"] == "no_indicator"
    assert len(data["matched_indicators"]) == 0
    assert "No explicitly identified caller utterances available" in data["uncertainty_notes"]


def test_analyze_emergency_response_schema():
    """Test that response contains all expected fields."""
    payload = {
        "utterances": [
            {"text": "He collapsed", "speaker": "caller", "utterance_index": 0},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields present
    assert "status" in data
    assert "risk_category" in data
    assert "explanation" in data
    assert "matched_indicators" in data
    assert "contradictory_evidence" in data
    assert "rule_identifiers" in data
    assert "requires_operator_confirmation" in data
    assert "uncertainty_notes" in data
    assert "detector_version" in data

    # Verify matched indicators structure
    if data["matched_indicators"]:
        indicator = data["matched_indicators"][0]
        assert "phrase" in indicator
        assert "category" in indicator
        assert "utterance_index" in indicator
        assert "utterance_text" in indicator
        assert "speaker" in indicator


def test_analyze_emergency_case_insensitive():
    """Test case-insensitive phrase matching."""
    payload = {
        "utterances": [
            {"text": "HE IS UNCONSCIOUS", "speaker": "caller", "utterance_index": 0},
            {"text": "NOT BREATHING", "speaker": "caller", "utterance_index": 1},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "potential_emergency"


def test_analyze_emergency_three_utterance_window():
    """Test that only latest 3 caller utterances are analyzed."""
    payload = {
        "utterances": [
            {"text": "He collapsed", "speaker": "caller", "utterance_index": 0},
            {"text": "Not breathing", "speaker": "caller", "utterance_index": 1},
            {"text": "Normal conversation", "speaker": "caller", "utterance_index": 2},
            {"text": "More talking", "speaker": "caller", "utterance_index": 3},
            {"text": "Even more", "speaker": "caller", "utterance_index": 4},
        ]
    }
    response = client.post("/api/v1/emergency/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    # Latest 3 are indices 2, 3, 4 - no indicators there
    assert data["status"] == "no_indicator"


def test_analyze_emergency_explanation_exists():
    """Test that explanation is always provided."""
    test_cases = [
        {
            "utterances": [
                {"text": "unconscious", "speaker": "caller", "utterance_index": 0},
                {"text": "not breathing", "speaker": "caller", "utterance_index": 1},
            ]
        },
        {
            "utterances": [
                {"text": "unconscious", "speaker": "caller", "utterance_index": 0},
            ]
        },
        {
            "utterances": [
                {"text": "everything fine", "speaker": "caller", "utterance_index": 0},
            ]
        },
    ]

    for payload in test_cases:
        response = client.post("/api/v1/emergency/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["explanation"]
        assert len(data["explanation"]) > 0


def test_emergency_endpoint_documented_in_openapi():
    """Test that emergency endpoint appears in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    assert "/api/v1/emergency/analyze" in schema["paths"]
    endpoint = schema["paths"]["/api/v1/emergency/analyze"]["post"]
    assert endpoint["tags"] == ["emergency"]
    assert "summary" in endpoint
    assert "description" in endpoint
