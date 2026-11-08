"""Deterministic emergency indicator detection engine.

This module implements explainable, rule-based emergency phrase detection
for multilingual emergency call transcripts. It uses only deterministic
pattern matching and does not involve LLMs or probabilistic models.

Medical Disclaimer:
This is a decision-support prototype. All emergency indicators require
human operator review and confirmation. This system does not diagnose
medical conditions or authorize ambulance dispatch.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class DetectionStatus(str, Enum):
    """Detection outcome status."""

    NO_INDICATOR = "no_indicator"
    REVIEW_REQUIRED = "review_required"
    POTENTIAL_EMERGENCY = "potential_emergency"


class RiskCategory(str, Enum):
    """Emergency risk classification."""

    NONE = "none"
    UNCERTAIN = "uncertain"
    CARDIAC_RESPIRATORY = "cardiac_respiratory"


# Phrase dictionaries for emergency indicators
# Each phrase is normalized lowercase for case-insensitive matching

UNRESPONSIVE_PHRASES = {
    # Kannada
    "ಎಚ್ಚರ ಇಲ್ಲ",  # no consciousness
    "ಎಚ್ಚರ ತಪ್ಪಿ",  # lost consciousness
    "ಮಾತಾಡ್ತಿಲ್ಲ",  # not speaking
    "ಸ್ಪಂದಿಸ್ತಿಲ್ಲ",  # not responding
    "ಬಿದ್ದುಬಿಟ್ರು",  # collapsed
    # Hindi
    "बेहोश",  # unconscious
    "होश नहीं",  # no consciousness
    "जवाब नहीं",  # no response
    "गिर गए",  # fell down/collapsed
    # English
    "unconscious",
    "not responding",
    "collapsed",
    "fainted",
    "unresponsive",
    "no response",
}

ABNORMAL_BREATHING_PHRASES = {
    # Kannada
    "ಉಸಿರಾಡ್ತಿಲ್ಲ",  # not breathing
    "ಉಸಿರು ಇಲ್ಲ",  # no breath
    "ಉಸಿರು ನಿಂತಿದೆ",  # breathing stopped
    # Hindi
    "साँस नहीं",  # no breath
    "सांस नहीं",  # no breath (alternate spelling)
    "सांस रुक गई",  # breathing stopped
    # English
    "not breathing",
    "no normal breathing",
    "gasping",
    "no breathing",
    "stopped breathing",
}

# Negation and contradiction patterns
NEGATION_INDICATORS = {
    # English
    "is breathing",
    "breathing normally",
    "is awake",
    "is conscious",
    "responding now",
    "awake now",
    # Kannada
    "ಉಸಿರಾಡ್ತಾ ಇದ್ದಾರೆ",  # is breathing
    "ಎಚ್ಚರವಾಗಿದ್ದಾರೆ",  # is awake/conscious
    # Hindi
    "सांस ले रहा है",  # is breathing
    "होश में है",  # is conscious
}

PAST_TENSE_INDICATORS = {
    "was unconscious",
    "was not breathing",
    "earlier",
    "before",
    "previously",
}


@dataclass(frozen=True)
class Utterance:
    """A single utterance from the call transcript with full context.
    
    Supports both manually segmented and automatically diarized transcripts.
    Optional fields allow gradual enhancement as audio processing improves.
    """

    text: str
    """Original transcript text, preserved without modification."""
    
    speaker: str | None = None
    """Speaker identity: 'caller', 'operator', or None if unknown."""
    
    utterance_index: int = 0
    """Sequential position in the conversation (0-indexed)."""
    
    utterance_id: str = field(default_factory=lambda: str(uuid4()))
    """Unique identifier for this utterance."""
    
    timestamp: float | None = None
    """Optional timestamp in seconds from call start."""
    
    language: str | None = None
    """Detected or declared language code (e.g., 'kn', 'en', 'hi', 'mixed')."""
    
    confidence: float | None = None
    """Optional transcription confidence (0.0-1.0) if available from ASR."""
    
    source: str = "manual"
    """Source of utterance: 'manual', 'diarization', 'sentence_boundary'."""


@dataclass(frozen=True)
class MatchedIndicator:
    """A detected emergency phrase match with full traceability."""

    phrase: str
    """The exact phrase that was matched from the dictionary."""
    
    category: str
    """Indicator category: 'unresponsive' or 'abnormal_breathing'."""
    
    utterance_index: int
    """Sequential position of the source utterance."""
    
    utterance_id: str
    """Unique identifier of the source utterance."""
    
    utterance_text: str
    """Complete original text of the utterance containing the match."""
    
    speaker: str | None
    """Speaker who produced this utterance."""


@dataclass(frozen=True)
class DetectionResult:
    """Structured emergency detection result with full explainability."""

    status: DetectionStatus
    risk_category: RiskCategory
    explanation: str
    matched_indicators: list[MatchedIndicator]
    contradictory_evidence: list[str]
    rule_identifiers: list[str]
    requires_operator_confirmation: bool
    uncertainty_notes: list[str]
    detector_version: str = "1.1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "status": self.status.value,
            "risk_category": self.risk_category.value,
            "explanation": self.explanation,
            "matched_indicators": [
                {
                    "phrase": m.phrase,
                    "category": m.category,
                    "utterance_index": m.utterance_index,
                    "utterance_id": m.utterance_id,
                    "utterance_text": m.utterance_text,
                    "speaker": m.speaker,
                }
                for m in self.matched_indicators
            ],
            "contradictory_evidence": self.contradictory_evidence,
            "rule_identifiers": self.rule_identifiers,
            "requires_operator_confirmation": self.requires_operator_confirmation,
            "uncertainty_notes": self.uncertainty_notes,
            "detector_version": self.detector_version,
        }


class EmergencyDetector:
    """Deterministic emergency indicator detection engine."""

    def __init__(self) -> None:
        """Initialize the detector with phrase dictionaries."""
        self.unresponsive_phrases = UNRESPONSIVE_PHRASES
        self.abnormal_breathing_phrases = ABNORMAL_BREATHING_PHRASES
        self.negation_indicators = NEGATION_INDICATORS
        self.past_tense_indicators = PAST_TENSE_INDICATORS

    def analyze(self, utterances: list[Utterance]) -> DetectionResult:
        """Analyze transcript utterances for emergency indicators.

        Core Rule (RULE_001):
        A potential emergency indicator is raised when BOTH conditions are met
        within the latest three caller utterances:
        1. At least one unresponsive indicator
        2. At least one abnormal breathing indicator

        Args:
            utterances: List of transcript utterances in chronological order.

        Returns:
            DetectionResult with status, matched phrases, and explanation.
        """
        if not utterances:
            return DetectionResult(
                status=DetectionStatus.NO_INDICATOR,
                risk_category=RiskCategory.NONE,
                explanation="No transcript data available for analysis.",
                matched_indicators=[],
                contradictory_evidence=[],
                rule_identifiers=[],
                requires_operator_confirmation=False,
                uncertainty_notes=["Empty transcript provided"],
            )

        # Extract latest three caller utterances (RULE_001 window)
        caller_utterances = [u for u in utterances if u.speaker != "operator"]
        latest_three = caller_utterances[-3:] if len(caller_utterances) >= 3 else caller_utterances

        if not latest_three:
            return DetectionResult(
                status=DetectionStatus.NO_INDICATOR,
                risk_category=RiskCategory.NONE,
                explanation="No caller utterances found in the transcript.",
                matched_indicators=[],
                contradictory_evidence=[],
                rule_identifiers=[],
                requires_operator_confirmation=False,
                uncertainty_notes=["Only operator speech detected"],
            )

        # Detect matches
        unresponsive_matches = self._find_matches(
            latest_three, self.unresponsive_phrases, "unresponsive"
        )
        breathing_matches = self._find_matches(
            latest_three, self.abnormal_breathing_phrases, "abnormal_breathing"
        )
        contradictions = self._find_contradictions(utterances)

        all_matches = unresponsive_matches + breathing_matches
        has_unresponsive = len(unresponsive_matches) > 0
        has_abnormal_breathing = len(breathing_matches) > 0
        has_contradictions = len(contradictions) > 0

        # Apply detection rules
        if has_unresponsive and has_abnormal_breathing:
            # Both indicators present - potential emergency
            if has_contradictions:
                return DetectionResult(
                    status=DetectionStatus.REVIEW_REQUIRED,
                    risk_category=RiskCategory.UNCERTAIN,
                    explanation=(
                        "Both unresponsive and abnormal breathing indicators detected, "
                        "but contradictory information is also present. Operator review required."
                    ),
                    matched_indicators=all_matches,
                    contradictory_evidence=contradictions,
                    rule_identifiers=["RULE_001", "CONTRADICTION_DETECTED"],
                    requires_operator_confirmation=True,
                    uncertainty_notes=[
                        "Contradictory statements found in transcript",
                        "Caller may have corrected earlier information",
                    ],
                )
            else:
                return DetectionResult(
                    status=DetectionStatus.POTENTIAL_EMERGENCY,
                    risk_category=RiskCategory.CARDIAC_RESPIRATORY,
                    explanation=(
                        "Potential cardiac-respiratory emergency detected. "
                        "Caller reports person is unresponsive and not breathing normally. "
                        "Immediate operator confirmation and CPR protocol review required."
                    ),
                    matched_indicators=all_matches,
                    contradictory_evidence=[],
                    rule_identifiers=["RULE_001"],
                    requires_operator_confirmation=True,
                    uncertainty_notes=[],
                )

        elif has_unresponsive or has_abnormal_breathing:
            # Only one indicator - needs review
            category = "unresponsive" if has_unresponsive else "abnormal breathing"
            return DetectionResult(
                status=DetectionStatus.REVIEW_REQUIRED,
                risk_category=RiskCategory.UNCERTAIN,
                explanation=(
                    f"Single {category} indicator detected, but not both required "
                    "indicators for emergency classification. Further assessment needed."
                ),
                matched_indicators=all_matches,
                contradictory_evidence=contradictions,
                rule_identifiers=["RULE_001_PARTIAL"],
                requires_operator_confirmation=True,
                uncertainty_notes=[
                    f"Only {category} indicator present",
                    "Missing complementary indicator for emergency classification",
                ],
            )

        else:
            # No indicators
            return DetectionResult(
                status=DetectionStatus.NO_INDICATOR,
                risk_category=RiskCategory.NONE,
                explanation="No emergency indicators detected in the analyzed utterances.",
                matched_indicators=[],
                contradictory_evidence=contradictions,
                rule_identifiers=[],
                requires_operator_confirmation=False,
                uncertainty_notes=[],
            )

    def _find_matches(
        self, utterances: list[Utterance], phrases: set[str], category: str
    ) -> list[MatchedIndicator]:
        """Find phrase matches in utterances with duplicate prevention."""
        matches = []
        seen_combinations = set()  # Prevent duplicate matches: (utterance_id, phrase)
        
        for utterance in utterances:
            text_lower = utterance.text.lower()
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    # Prevent duplicate detection of same phrase in same utterance
                    combo_key = (utterance.utterance_id, phrase)
                    if combo_key in seen_combinations:
                        continue
                    seen_combinations.add(combo_key)
                    
                    matches.append(
                        MatchedIndicator(
                            phrase=phrase,
                            category=category,
                            utterance_index=utterance.utterance_index,
                            utterance_id=utterance.utterance_id,
                            utterance_text=utterance.text,
                            speaker=utterance.speaker,
                        )
                    )
        return matches

    def _find_contradictions(self, utterances: list[Utterance]) -> list[str]:
        """Detect contradictory or negating statements."""
        contradictions = []

        for utterance in utterances:
            text_lower = utterance.text.lower()

            # Check for negation indicators
            for negation in self.negation_indicators:
                if negation.lower() in text_lower:
                    contradictions.append(
                        f"Negation detected: '{utterance.text}' "
                        f"(utterance {utterance.utterance_index}, ID: {utterance.utterance_id[:8]})"
                    )
                    break

            # Check for past tense indicators
            for past in self.past_tense_indicators:
                if past.lower() in text_lower:
                    contradictions.append(
                        f"Past tense detected: '{utterance.text}' "
                        f"(utterance {utterance.utterance_index}, ID: {utterance.utterance_id[:8]})"
                    )
                    break

        return contradictions
