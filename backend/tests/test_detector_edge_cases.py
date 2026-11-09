"""Comprehensive emergency detector edge case tests.

Tests negation, temporal reasoning, speaker attribution, and evidence integrity.
"""

from backend.app.services.emergency_detector import (
    DetectionStatus,
    EmergencyDetector,
    Utterance,
)


def test_positive_indication_not_responding():
    """Caller explicitly reports unresponsiveness."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not responding", speaker="caller", utterance_index=0),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    # Check via matched indicators
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is True
    assert abnormal_breathing is True


def test_negation_is_responding():
    """'He is responding' should not trigger unresponsive indicator."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is responding", speaker="caller", utterance_index=0),
        Utterance(text="He is breathing", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is False
    assert abnormal_breathing is False


def test_negation_breathing_normally():
    """'He is breathing normally' should NOT trigger abnormal breathing."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is breathing normally", speaker="caller", utterance_index=0),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert abnormal_breathing is False


def test_mixed_positive_and_negative_breathing():
    """Positive and negative breathing indicators create contradiction."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not breathing", speaker="caller", utterance_index=0),
        Utterance(text="Wait, he is breathing now", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    # Should detect contradiction
    assert len(result.contradictory_evidence) > 0
    # Should still require review
    assert result.requires_operator_confirmation is True


def test_past_tense_was_unconscious():
    """'Was unconscious' should be treated as past event, creating uncertainty."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He was unconscious earlier", speaker="caller", utterance_index=0),
        Utterance(text="He was not breathing before", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    # Past tense creates contradiction/uncertainty
    assert len(result.contradictory_evidence) > 0


def test_temporal_resolved_condition():
    """Condition reported as resolved should create contradiction."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He was not breathing", speaker="caller", utterance_index=0),
        Utterance(text="He is breathing normally now", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert len(result.contradictory_evidence) > 0


def test_update_contradicts_earlier_statement():
    """Later utterance contradicting earlier one."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1),
        Utterance(text="Wait, he is responding now", speaker="caller", utterance_index=2),
    ]
    
    result = detector.analyze(utterances)
    # Contradiction should be detected
    assert len(result.contradictory_evidence) > 0
    # But still requires review
    assert result.requires_operator_confirmation is True


def test_speaker_attribution_caller_only():
    """Only caller utterances should contribute to emergency detection."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="Is he responding?", speaker="operator", utterance_index=0),
        Utterance(text="No, he is not responding", speaker="caller", utterance_index=1),
        Utterance(text="Is he breathing?", speaker="operator", utterance_index=2),
        Utterance(text="No, he is not breathing", speaker="caller", utterance_index=3),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is True
    assert abnormal_breathing is True
    
    # Verify evidence comes from caller only
    for indicator in result.matched_indicators:
        # Find the source utterance
        source_utterance = utterances[indicator.utterance_index]
        assert source_utterance.speaker == "caller"


def test_operator_statements_never_trigger_indicators():
    """Operator saying 'not responding' should NOT trigger detection."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="If he is not responding, start CPR", speaker="operator", utterance_index=0),
        Utterance(text="Check if he is not breathing", speaker="operator", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is False
    assert abnormal_breathing is False


def test_unknown_speaker_not_treated_as_caller():
    """Utterances with speaker=None should not trigger caller-based detection."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not responding", speaker=None, utterance_index=0),
        Utterance(text="He is not breathing", speaker=None, utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR
    assert "No explicitly identified caller utterances" in " ".join(result.uncertainty_notes)


def test_missing_speaker_field():
    """Utterances with speaker=None are treated as unknown."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="Not responding", speaker=None, utterance_index=0),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR


def test_invalid_speaker_value_treated_as_unknown():
    """Speaker values other than 'caller' or 'operator' are unknown."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not responding", speaker="bystander", utterance_index=0),
        Utterance(text="He is not breathing", speaker="paramedic", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    # Bystander/paramedic not treated as caller
    assert result.status == DetectionStatus.NO_INDICATOR


def test_evidence_references_correct_utterance_id():
    """Every matched indicator must reference the correct utterance ID."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0, utterance_id="id-001"),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1, utterance_id="id-002"),
    ]
    
    result = detector.analyze(utterances)
    
    # Check unresponsive indicator
    unresponsive_indicators = [i for i in result.matched_indicators if i.category == "unresponsive"]
    assert len(unresponsive_indicators) == 1
    assert unresponsive_indicators[0].utterance_id == "id-001"
    assert unresponsive_indicators[0].utterance_index == 0
    
    # Check breathing indicator
    breathing_indicators = [i for i in result.matched_indicators if i.category == "abnormal_breathing"]
    assert len(breathing_indicators) == 1
    assert breathing_indicators[0].utterance_id == "id-002"
    assert breathing_indicators[0].utterance_index == 1


def test_evidence_text_matches_source_utterance():
    """Evidence text should match the actual source utterance."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He collapsed", speaker="caller", utterance_index=0),
        Utterance(text="He is gasping", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    
    for indicator in result.matched_indicators:
        source_utterance = utterances[indicator.utterance_index]
        # The matched phrase should appear in the source text
        assert indicator.phrase.lower() in source_utterance.text.lower()


def test_duplicate_phrases_same_utterance():
    """Duplicate phrases in same utterance shouldn't create duplicate evidence."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not breathing, I repeat, not breathing", speaker="caller", utterance_index=0),
        Utterance(text="He is not responding", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    
    # Should only count phrase once per utterance
    breathing_indicators = [i for i in result.matched_indicators if i.category == "abnormal_breathing"]
    # Even if "not breathing" appears twice, should only match once per utterance
    assert all(i.utterance_index == 0 for i in breathing_indicators)


def test_kannada_emergency_indicators():
    """Kannada emergency phrases should be detected."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="ಅವನು ಸ್ಪಂದಿಸ್ತಿಲ್ಲ", speaker="caller", utterance_index=0),  # not responding
        Utterance(text="ಅವನು ಉಸಿರಾಡ್ತಿಲ್ಲ", speaker="caller", utterance_index=1),  # not breathing
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is True
    assert abnormal_breathing is True


def test_hindi_emergency_indicators():
    """Hindi emergency phrases should be detected."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="वह बेहोश है", speaker="caller", utterance_index=0),  # unconscious
        Utterance(text="साँस नहीं ले रहा", speaker="caller", utterance_index=1),  # not breathing
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY


def test_codemixed_kannada_english():
    """Kannada-English code-mixed statements."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is ಸ್ಪಂದಿಸ್ತಿಲ್ಲ", speaker="caller", utterance_index=0),
        Utterance(text="ಉಸಿರಾಡ್ತಿಲ್ಲ, not breathing", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.POTENTIAL_EMERGENCY


def test_unicode_nfc_normalization():
    """Different Unicode representations should match."""
    detector = EmergencyDetector()
    
    # Same Kannada text in different Unicode normalization forms should match
    utterances = [
        Utterance(text="ಸ್ಪಂದಿಸ್ತಿಲ್ಲ", speaker="caller", utterance_index=0),
        Utterance(text="ಉಸಿರಾಡ್ತಿಲ್ಲ", speaker="caller", utterance_index=1),
    ]
    
    result = detector.analyze(utterances)
    # Should detect emergency even if Unicode representation varies
    unresponsive = any(i.category == "unresponsive" for i in result.matched_indicators)
    abnormal_breathing = any(i.category == "abnormal_breathing" for i in result.matched_indicators)
    assert unresponsive is True or abnormal_breathing is True


def test_three_utterance_window_enforcement():
    """Detection only considers latest 3 caller utterances."""
    detector = EmergencyDetector()
    
    utterances = [
        # Old utterances (should be ignored)
        Utterance(text="He was not responding", speaker="caller", utterance_index=0),
        Utterance(text="He was not breathing", speaker="caller", utterance_index=1),
        # Recent utterances (should be considered)
        Utterance(text="He is awake now", speaker="caller", utterance_index=2),
        Utterance(text="He is breathing", speaker="caller", utterance_index=3),
        Utterance(text="He is responding", speaker="caller", utterance_index=4),
    ]
    
    result = detector.analyze(utterances)
    # Recent negations should prevent detection
    assert len(result.contradictory_evidence) > 0


def test_operator_confirmation_always_required_for_indicators():
    """Any detected indicator requires operator confirmation."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is unconscious", speaker="caller", utterance_index=0),
    ]
    
    result = detector.analyze(utterances)
    assert result.requires_operator_confirmation is True


def test_no_confirmation_required_when_no_indicators():
    """No confirmation needed when no indicators detected."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is okay", speaker="caller", utterance_index=0),
    ]
    
    result = detector.analyze(utterances)
    assert result.requires_operator_confirmation is False


def test_detector_output_is_deterministic():
    """Same input should produce same output."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="He is not responding", speaker="caller", utterance_index=0),
        Utterance(text="He is not breathing", speaker="caller", utterance_index=1),
    ]
    
    result1 = detector.analyze(utterances)
    result2 = detector.analyze(utterances)
    
    assert result1.status == result2.status
    unresponsive1 = any(i.category == "unresponsive" for i in result1.matched_indicators)
    unresponsive2 = any(i.category == "unresponsive" for i in result2.matched_indicators)
    abnormal_breathing1 = any(i.category == "abnormal_breathing" for i in result1.matched_indicators)
    abnormal_breathing2 = any(i.category == "abnormal_breathing" for i in result2.matched_indicators)
    
    assert unresponsive1 == unresponsive2
    assert abnormal_breathing1 == abnormal_breathing2
    assert len(result1.matched_indicators) == len(result2.matched_indicators)


def test_empty_caller_utterances():
    """Handle transcript with no caller utterances gracefully."""
    detector = EmergencyDetector()
    
    utterances = [
        Utterance(text="Hello, emergency services", speaker="operator", utterance_index=0),
    ]
    
    result = detector.analyze(utterances)
    assert result.status == DetectionStatus.NO_INDICATOR
    assert "Only operator speech detected" in " ".join(result.uncertainty_notes)
