"""Competition demonstration scenarios for emergency detection.

These tests validate realistic emergency call scenarios that will be demonstrated
during the competition submission, including code-mixed Kannada-English cases.
"""

import pytest

from backend.app.services.emergency_detector import (
    DetectionStatus,
    EmergencyDetector,
    RiskCategory,
    Utterance,
)


@pytest.fixture
def detector() -> EmergencyDetector:
    """Provide a fresh detector instance."""
    return EmergencyDetector()


def test_realistic_kannada_english_cardiac_emergency(detector):
    """Test realistic Kannada-English code-mixed cardiac arrest call."""
    utterances = [
        Utterance(
            text="Hello, 108 ge phone maadidini",  # Called 108
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="What is your emergency?",
            speaker="operator",
            utterance_index=1,
        ),
        Utterance(
            text="Nanna appa ಬಿದ್ದುಬಿಟ್ರು, chest pain antha heLidru",  # My father collapsed
            speaker="caller",
            utterance_index=2,
        ),
        Utterance(
            text="Is he conscious? Can he talk?",
            speaker="operator",
            utterance_index=3,
        ),
        Utterance(
            text="ಎಚ್ಚರ ಇಲ್ಲ sir, ಉಸಿರಾಡ್ತಿಲ್ಲ",  # Not conscious, not breathing
            speaker="caller",
            utterance_index=4,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # Should detect BOTH indicators in latest 3 caller utterances (0, 2, 4)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert result.risk_category == RiskCategory.CARDIAC_RESPIRATORY
    assert len(result.matched_indicators) == 3  # collapsed + not conscious + not breathing
    
    # Verify both categories
    categories = {m.category for m in result.matched_indicators}
    assert "unresponsive" in categories
    assert "abnormal_breathing" in categories
    
    assert result.requires_operator_confirmation is True
    assert "RULE_001" in result.rule_identifiers


def test_false_alarm_caller_corrects_themselves(detector):
    """Test caller self-correction scenario."""
    utterances = [
        Utterance(
            text="My mother fainted",
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="Is she breathing?",
            speaker="operator",
            utterance_index=1,
        ),
        Utterance(
            text="Wait, she is awake now, breathing normally",
            speaker="caller",
            utterance_index=2,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # Latest 3 caller utterances are 0, 2 (only 2 caller utterances exist)
    # Should detect "fainted" but also "awake now" and "breathing normally"
    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert len(result.contradictory_evidence) > 0
    
    # Should still require operator confirmation due to initial indicator
    assert result.requires_operator_confirmation is True


def test_non_emergency_chest_pain_conscious(detector):
    """Test non-emergency chest pain with conscious patient."""
    utterances = [
        Utterance(
            text="My husband has chest pain",
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="Is he conscious?",
            speaker="operator",
            utterance_index=1,
        ),
        Utterance(
            text="Yes, he is responding and breathing",
            speaker="caller",
            utterance_index=2,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # No emergency indicators - chest pain alone is not in phrase dictionary
    assert result.status == DetectionStatus.NO_INDICATOR
    assert result.risk_category == RiskCategory.NONE
    assert len(result.matched_indicators) == 0
    assert result.requires_operator_confirmation is False


def test_hindi_emergency_detection(detector):
    """Test Hindi emergency phrase detection."""
    utterances = [
        Utterance(
            text="मेरे पिता बेहोश हैं",  # My father is unconscious
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="क्या वह सांस ले रहे हैं?",  # Is he breathing?
            speaker="operator",
            utterance_index=1,
        ),
        Utterance(
            text="नहीं, साँस नहीं",  # No, not breathing
            speaker="caller",
            utterance_index=2,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert result.risk_category == RiskCategory.CARDIAC_RESPIRATORY
    
    # Verify both indicators detected
    categories = {m.category for m in result.matched_indicators}
    assert "unresponsive" in categories
    assert "abnormal_breathing" in categories


def test_operator_utterances_correctly_excluded(detector):
    """Verify operator speech does not trigger false positives."""
    utterances = [
        Utterance(
            text="Tell me if he is unconscious",
            speaker="operator",
            utterance_index=0,
        ),
        Utterance(
            text="Check if he is not breathing",
            speaker="operator",
            utterance_index=1,
        ),
        Utterance(
            text="He is talking to me",
            speaker="caller",
            utterance_index=2,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # Operator mentions "unconscious" and "not breathing" but should be ignored
    # Only caller utterance (index 2) should be analyzed
    assert result.status == DetectionStatus.NO_INDICATOR
    assert len(result.matched_indicators) == 0


def test_partial_phrase_no_false_positive(detector):
    """Ensure partial phrase matches don't trigger false positives."""
    utterances = [
        Utterance(
            text="He was unconscious earlier but is awake now",  # Past tense
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="He was not breathing before but breathing now",  # Past tense
            speaker="caller",
            utterance_index=1,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # Both indicators present BUT contradictions detected
    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert len(result.contradictory_evidence) >= 2  # Past tense detected
    
    # Should still match the indicators
    assert len(result.matched_indicators) == 2


def test_unknown_speaker_treated_as_caller(detector):
    """Verify unknown speaker utterances are analyzed (treated as caller)."""
    utterances = [
        Utterance(
            text="Person collapsed",
            speaker=None,  # Unknown speaker
            utterance_index=0,
        ),
        Utterance(
            text="Not breathing",
            speaker=None,  # Unknown speaker
            utterance_index=1,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # Unknown speakers should be analyzed (not excluded like operators)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_gasping_detected_as_abnormal_breathing(detector):
    """Verify 'gasping' is recognized as abnormal breathing indicator."""
    utterances = [
        Utterance(
            text="He is unconscious on the floor",
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(
            text="He is gasping for air",
            speaker="caller",
            utterance_index=1,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    
    # Check that gasping is categorized as abnormal_breathing
    breathing_indicators = [
        m for m in result.matched_indicators if m.category == "abnormal_breathing"
    ]
    assert len(breathing_indicators) > 0
    assert any("gasping" in m.phrase.lower() for m in breathing_indicators)


def test_only_operator_speech_no_false_emergency(detector):
    """Verify calls with only operator speech don't trigger false alarms."""
    utterances = [
        Utterance(
            text="Emergency services, what is your location?",
            speaker="operator",
            utterance_index=0,
        ),
        Utterance(
            text="If patient is unconscious and not breathing, start CPR",
            speaker="operator",
            utterance_index=1,
        ),
    ]
    
    result = detector.analyze(utterances)
    
    # No caller utterances - should not trigger emergency
    assert result.status == DetectionStatus.NO_INDICATOR
    assert len(result.matched_indicators) == 0
    assert "Only operator speech detected" in result.uncertainty_notes
