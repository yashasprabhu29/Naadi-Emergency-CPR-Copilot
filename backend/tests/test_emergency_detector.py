"""Tests for the deterministic emergency detection engine."""

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


def test_both_indicators_triggers_potential_emergency(detector):
    """Test that both unresponsive + abnormal breathing triggers emergency."""
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert result.risk_category == RiskCategory.CARDIAC_RESPIRATORY
    assert len(result.matched_indicators) == 2
    assert result.requires_operator_confirmation is True
    assert "RULE_001" in result.rule_identifiers
    assert len(result.contradictory_evidence) == 0


def test_unresponsive_only_requires_review(detector):
    """Test that unresponsive alone does not trigger emergency."""
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert result.risk_category == RiskCategory.UNCERTAIN
    assert len(result.matched_indicators) == 1
    assert result.matched_indicators[0].category == "unresponsive"
    assert "RULE_001_PARTIAL" in result.rule_identifiers


def test_abnormal_breathing_only_requires_review(detector):
    """Test that breathing issue alone does not trigger emergency."""
    utterances = [
        Utterance(text="He is not breathing", speaker="caller", utterance_index=0),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert result.risk_category == RiskCategory.UNCERTAIN
    assert len(result.matched_indicators) == 1
    assert result.matched_indicators[0].category == "abnormal_breathing"


def test_both_indicators_in_separate_utterances(detector):
    """Test detection across multiple utterances."""
    utterances = [
        Utterance(text="My father collapsed", speaker="caller", utterance_index=0),
        Utterance(text="What happened?", speaker="operator", utterance_index=1),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=2),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2
    # Verify both categories present
    categories = {m.category for m in result.matched_indicators}
    assert "unresponsive" in categories
    assert "abnormal_breathing" in categories


def test_indicators_outside_three_utterance_window(detector):
    """Test that indicators beyond latest 3 caller utterances are not counted."""
    utterances = [
        Utterance(text="He collapsed", speaker="caller", utterance_index=0),
        Utterance(text="He was not breathing", speaker="caller", utterance_index=1),
        Utterance(text="Normal conversation", speaker="caller", utterance_index=2),
        Utterance(text="More conversation", speaker="caller", utterance_index=3),
        Utterance(text="Even more talking", speaker="caller", utterance_index=4),
    ]
    result = detector.analyze(utterances)

    # Latest 3 are utterances 2, 3, 4 - no indicators there
    assert result.status == DetectionStatus.NO_INDICATOR


def test_contradictory_evidence_triggers_review(detector):
    """Test that contradictions change status to review_required."""
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1),
        Utterance(text="Wait, he is breathing normally now", speaker="caller", utterance_index=2),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert result.risk_category == RiskCategory.UNCERTAIN
    assert len(result.contradictory_evidence) > 0
    assert "CONTRADICTION_DETECTED" in result.rule_identifiers
    assert any("Negation detected" in c for c in result.contradictory_evidence)


def test_negation_detected(detector):
    """Test that negation phrases are detected."""
    utterances = [
        Utterance(text="She is breathing normally", speaker="caller", utterance_index=0),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.NO_INDICATOR
    # Should detect negation even without emergency indicators
    contradictions = detector._find_contradictions(utterances)
    assert len(contradictions) > 0


def test_past_tense_detected(detector):
    """Test that past tense indicators are detected."""
    utterances = [
        Utterance(text="He was unconscious earlier", speaker="caller", utterance_index=0),
        Utterance(text="He was not breathing before", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    # Both indicators present, but past tense creates contradiction
    assert result.status == DetectionStatus.REVIEW_REQUIRED
    assert len(result.contradictory_evidence) > 0


def test_kannada_phrases_detected(detector):
    """Test Kannada emergency phrases."""
    utterances = [
        Utterance(text="ಅವರು ಎಚ್ಚರ ಇಲ್ಲ", speaker="caller", utterance_index=0),
        Utterance(text="ಉಸಿರಾಡ್ತಿಲ್ಲ", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_hindi_phrases_detected(detector):
    """Test Hindi emergency phrases."""
    utterances = [
        Utterance(text="वो बेहोश है", speaker="caller", utterance_index=0),
        Utterance(text="साँस नहीं आ रही", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_english_phrases_detected(detector):
    """Test English emergency phrases."""
    utterances = [
        Utterance(text="Patient is unresponsive", speaker="caller", utterance_index=0),
        Utterance(text="No normal breathing observed", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_mixed_language_detection(detector):
    """Test mixed Kannada-English codemix."""
    utterances = [
        Utterance(text="ನನ್ನ father unconscious ಆಗಿದ್ದಾರೆ", speaker="caller", utterance_index=0),
        Utterance(text="ಉಸಿರು ಇಲ್ಲ completely", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_empty_transcript_returns_no_indicator(detector):
    """Test that empty input is handled safely."""
    result = detector.analyze([])

    assert result.status == DetectionStatus.NO_INDICATOR
    assert result.risk_category == RiskCategory.NONE
    assert len(result.uncertainty_notes) > 0
    assert "Empty transcript" in result.uncertainty_notes[0]


def test_operator_only_utterances(detector):
    """Test that operator-only speech returns no indicator."""
    utterances = [
        Utterance(text="Emergency services, what is your location?", speaker="operator", utterance_index=0),
        Utterance(text="Can you describe the situation?", speaker="operator", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.NO_INDICATOR
    assert "No caller utterances" in result.explanation


def test_duplicate_phrases_in_same_utterance(detector):
    """Test handling of repeated phrases."""
    utterances = [
        Utterance(
            text="He is unconscious, completely unconscious",
            speaker="caller",
            utterance_index=0,
        ),
        Utterance(text="Not breathing at all", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    # May detect multiple matches, which is acceptable


def test_normal_breathing_statement_no_indicator(detector):
    """Test that normal breathing statement does not trigger."""
    utterances = [
        Utterance(text="He is breathing normally", speaker="caller", utterance_index=0),
        Utterance(text="He is awake", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.NO_INDICATOR


def test_corrected_statement_creates_uncertainty(detector):
    """Test that caller corrections create contradictory evidence."""
    utterances = [
        Utterance(text="He was not responding", speaker="caller", utterance_index=0),
        Utterance(text="Wait, he is responding now", speaker="caller", utterance_index=1),
        Utterance(text="He stopped breathing", speaker="caller", utterance_index=2),
    ]
    result = detector.analyze(utterances)

    # Has abnormal breathing indicator and past unresponsive statement
    # Should detect contradiction from "responding now"
    assert len(result.contradictory_evidence) > 0


def test_unknown_speaker_treated_as_caller(detector):
    """Test that utterances with unknown speaker are analyzed."""
    utterances = [
        Utterance(text="Person collapsed", speaker=None, utterance_index=0),
        Utterance(text="Not breathing", speaker=None, utterance_index=1),
    ]
    result = detector.analyze(utterances)

    # Unknown speaker utterances should be analyzed
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY


def test_case_insensitive_matching(detector):
    """Test that matching is case-insensitive."""
    utterances = [
        Utterance(text="HE IS UNCONSCIOUS", speaker="caller", utterance_index=0),
        Utterance(text="NOT BREATHING", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    assert len(result.matched_indicators) == 2


def test_result_to_dict_serialization(detector):
    """Test that results can be serialized to dict."""
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
        Utterance(text="Not breathing", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert result_dict["status"] == "potential_emergency"
    assert "matched_indicators" in result_dict
    assert isinstance(result_dict["matched_indicators"], list)
    assert "detector_version" in result_dict


def test_requires_confirmation_always_true_for_indicators(detector):
    """Test that any detected indicator requires operator confirmation."""
    test_cases = [
        # Potential emergency
        [
            Utterance(text="unconscious", speaker="caller", utterance_index=0),
            Utterance(text="not breathing", speaker="caller", utterance_index=1),
        ],
        # Review required - single indicator
        [Utterance(text="unconscious", speaker="caller", utterance_index=0)],
        # Review required - with contradiction
        [
            Utterance(text="unconscious", speaker="caller", utterance_index=0),
            Utterance(text="not breathing", speaker="caller", utterance_index=1),
            Utterance(text="breathing normally", speaker="caller", utterance_index=2),
        ],
    ]

    for utterances in test_cases:
        result = detector.analyze(utterances)
        if result.status != DetectionStatus.NO_INDICATOR:
            assert result.requires_operator_confirmation is True


def test_no_indicator_does_not_require_confirmation(detector):
    """Test that no indicator case does not require confirmation."""
    utterances = [
        Utterance(text="Everything is normal", speaker="caller", utterance_index=0),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.NO_INDICATOR
    assert result.requires_operator_confirmation is False


def test_gasping_detected_as_abnormal_breathing(detector):
    """Test that gasping is recognized as abnormal breathing."""
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
        Utterance(text="Only gasping", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    breathing_matches = [m for m in result.matched_indicators if m.category == "abnormal_breathing"]
    assert len(breathing_matches) == 1
    assert "gasping" in breathing_matches[0].phrase


def test_fainted_detected_as_unresponsive(detector):
    """Test that fainted is recognized as unresponsive."""
    utterances = [
        Utterance(text="She just fainted", speaker="caller", utterance_index=0),
        Utterance(text="Not breathing", speaker="caller", utterance_index=1),
    ]
    result = detector.analyze(utterances)

    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    unresponsive_matches = [m for m in result.matched_indicators if m.category == "unresponsive"]
    assert len(unresponsive_matches) == 1
    assert "fainted" in unresponsive_matches[0].phrase
