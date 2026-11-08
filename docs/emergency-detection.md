# Emergency Detection Engine — Technical Documentation

## Architecture

The emergency detection engine (`backend/app/services/emergency_detector.py`) is a standalone, deterministic rule-based system designed for multilingual emergency phrase detection. It operates independently of the transcription pipeline and does not use LLMs, machine learning models, or probabilistic inference.

## Design principles

1. **Explainable**: Every detection includes matched phrases, rule identifiers, and human-readable explanations
2. **Deterministic**: Same input always produces the same output
3. **Multilingual**: Supports Kannada, Hindi, and English phrase dictionaries
4. **Conservative**: Requires multiple indicators before raising potential emergency
5. **Transparent**: Exposes contradictions, uncertainty, and limitations
6. **Safety-first**: All results require human operator confirmation

## Detection workflow

```
Input: List[Utterance] → Filter caller utterances → Extract latest 3 →
Match phrases → Check contradictions → Apply rules → Output: DetectionResult
```

### Step 1: Utterance filtering

- Only caller utterances are analyzed (speaker != "operator")
- Utterances with `speaker=None` are treated as caller speech
- Operator questions and prompts are excluded from phrase matching

### Step 2: Three-utterance window (RULE_001)

Emergency detection analyzes only the **latest three caller utterances**. This window:
- Reduces false positives from past-tense descriptions
- Focuses on current emergency state
- Handles caller corrections naturally
- Aligns with real emergency call patterns

Example:
```python
utterances = [
    Utterance(text="He collapsed 10 minutes ago", speaker="caller", utterance_index=0),
    Utterance(text="He was not breathing", speaker="caller", utterance_index=1),
    # ... 3 more utterances ...
    Utterance(text="He's breathing now", speaker="caller", utterance_index=4),
]
# Only utterances 2, 3, 4 are analyzed
```

### Step 3: Phrase matching

The detector uses **substring matching** with case-insensitive comparison:

```python
if phrase.lower() in utterance.text.lower():
    # Match found
```

This approach:
- Works across codemixed transcripts (e.g., "ನನ್ನ father unconscious ಆಗಿದ್ದಾರೆ")
- Handles transcript variations and errors
- Supports partial matches within sentences
- Does not require tokenization or word boundaries

**Trade-off**: May match unintended substrings. Future improvements could add word-boundary detection.

### Step 4: Contradiction detection

Two types of contradictions are identified:

**A. Negation indicators**
Phrases indicating normal status:
- "is breathing", "breathing normally"
- "is awake", "is conscious"
- "responding now"

**B. Past tense indicators**
Time references suggesting past events:
- "was unconscious", "earlier", "before"

Contradictions change `potential_emergency` → `review_required` and add uncertainty notes.

### Step 5: Rule application

**RULE_001: Core emergency detection**

```
IF (unresponsive_matches >= 1 AND abnormal_breathing_matches >= 1):
    IF contradictions_present:
        status = REVIEW_REQUIRED
        risk = UNCERTAIN
    ELSE:
        status = POTENTIAL_EMERGENCY
        risk = CARDIAC_RESPIRATORY
ELSE IF (unresponsive_matches >= 1 OR abnormal_breathing_matches >= 1):
    status = REVIEW_REQUIRED
    risk = UNCERTAIN
ELSE:
    status = NO_INDICATOR
    risk = NONE
```

## Phrase dictionaries

### Unresponsive indicators

Phrases indicating loss of consciousness or responsiveness:

| Language | Phrase | Transliteration | Meaning |
|----------|--------|----------------|---------|
| Kannada | ಎಚ್ಚರ ಇಲ್ಲ | ecchara illa | No consciousness |
| Kannada | ಎಚ್ಚರ ತಪ್ಪಿ | ecchara tappi | Lost consciousness |
| Kannada | ಮಾತಾಡ್ತಿಲ್ಲ | maatadtilla | Not speaking |
| Kannada | ಸ್ಪಂದಿಸ್ತಿಲ್ಲ | spandisutilla | Not responding |
| Kannada | ಬಿದ್ದುಬಿಟ್ರು | biddubittru | Collapsed |
| Hindi | बेहोश | behosh | Unconscious |
| Hindi | होश नहीं | hosh nahin | No consciousness |
| Hindi | जवाब नहीं | javab nahin | No response |
| Hindi | गिर गए | gir gaye | Fell down/collapsed |
| English | unconscious | — | — |
| English | not responding | — | — |
| English | collapsed | — | — |
| English | fainted | — | — |
| English | unresponsive | — | — |

### Abnormal breathing indicators

Phrases indicating respiratory distress or arrest:

| Language | Phrase | Transliteration | Meaning |
|----------|--------|----------------|---------|
| Kannada | ಉಸಿರಾಡ್ತಿಲ್ಲ | usiradtilla | Not breathing |
| Kannada | ಉಸಿರು ಇಲ್ಲ | usiru illa | No breath |
| Kannada | ಉಸಿರು ನಿಂತಿದೆ | usiru nintide | Breathing stopped |
| Hindi | साँस नहीं | saans nahin | No breath |
| Hindi | सांस रुक गई | saans ruk gayi | Breathing stopped |
| English | not breathing | — | — |
| English | no normal breathing | — | — |
| English | gasping | — | — |
| English | stopped breathing | — | — |

## Response schema

```python
{
    "status": str,  # no_indicator | review_required | potential_emergency
    "risk_category": str,  # none | uncertain | cardiac_respiratory
    "explanation": str,  # Human-readable assessment
    "matched_indicators": [
        {
            "phrase": str,  # Exact matched phrase
            "category": str,  # unresponsive | abnormal_breathing
            "utterance_index": int,  # Position in conversation
            "utterance_text": str,  # Full utterance
            "speaker": str | null  # caller | operator | null
        }
    ],
    "contradictory_evidence": [str],  # Detected contradictions
    "rule_identifiers": [str],  # Applied rule codes
    "requires_operator_confirmation": bool,  # Always true for detections
    "uncertainty_notes": [str],  # Limitations and caveats
    "detector_version": str  # "1.0.0"
}
```

## Known edge cases

### Handled correctly

✅ Mixed-language utterances: "ನನ್ನ father unconscious ಆಗಿದ್ದಾರೆ"  
✅ Case variations: "UNCONSCIOUS", "Not Breathing"  
✅ Caller corrections: "Wait, he is breathing now"  
✅ Past tense: "He was unconscious earlier"  
✅ Operator-only speech: Excluded from analysis  
✅ Empty transcript: Returns no_indicator with uncertainty note  
✅ Single indicator: Triggers review_required, not potential_emergency  

### Known limitations

⚠️ **Word boundary issues**: "conscious" matches "unconscious"  
⚠️ **Negation scope**: "He is NOT unconscious" may still match "unconscious"  
⚠️ **Complex grammar**: "He stopped being unconscious" may confuse logic  
⚠️ **Transcript errors**: Misrecognized speech affects detection  
⚠️ **Multiple speakers**: Speaker diarization depends on upstream quality  
⚠️ **Sarcasm/questions**: "Is he unconscious?" matches indicator phrase  

Future improvements should address word boundaries and negation parsing.

## Testing approach

The test suite (`backend/tests/test_emergency_detector.py`) covers:

1. **Positive cases**: Both indicators present → potential_emergency
2. **Partial cases**: Single indicator → review_required
3. **Contradictions**: Both + negation → review_required
4. **Language coverage**: Kannada, Hindi, English, mixed
5. **Edge cases**: Empty input, operator-only, past tense, duplicates
6. **Window logic**: Indicators outside latest 3 utterances
7. **Serialization**: Result conversion to JSON-safe dict
8. **Confirmation**: All detections require operator confirmation

## Integration patterns

### Backend API integration

```python
from backend.app.services.emergency_detector import EmergencyDetector, Utterance

detector = EmergencyDetector()
utterances = [
    Utterance(text="He collapsed", speaker="caller", utterance_index=0),
    Utterance(text="Not breathing", speaker="caller", utterance_index=1),
]
result = detector.analyze(utterances)

if result.status == "potential_emergency":
    # Alert operator, log detection, activate protocol
    pass
```

### Frontend integration

Current implementation treats the full transcript as a single utterance:

```javascript
const utterances = [
  {
    text: transcription.transcript,
    speaker: "caller",
    utterance_index: 0,
  },
];
const analysis = await analyzeEmergency(utterances);
```

**Limitation**: Full transcript matching reduces detection accuracy. Ideal integration requires structured multi-utterance transcripts with speaker diarization and sentence segmentation.

## Future enhancements

### Short-term (Milestone 05)

- Add word-boundary detection to reduce false positives
- Improve negation scope parsing ("NOT unconscious")
- Extend phrase dictionaries with validated community input
- Add Tamil phrase support
- Implement operator acknowledgment logging

### Medium-term (Milestone 06+)

- WebSocket streaming with incremental detection
- Structured utterance parsing from Prisma output
- Speaker diarization integration
- Detection confidence scoring (without fabricated percentages)
- SQLite persistence for detection audit trail
- Integration with CPR protocol prompts

## Regulatory and clinical considerations

This system is a **research prototype** and decision-support tool. It is **not**:

❌ A medical device  
❌ Clinically validated  
❌ Approved for regulatory use  
❌ Authorized for unsupervised dispatch  
❌ Integrated with 108/112 infrastructure  

Any deployment beyond prototype testing requires:
- Clinical validation studies
- Regulatory approval (CDSCO or equivalent)
- Integration with certified emergency infrastructure
- Comprehensive operator training
- Audit and liability frameworks
- Continuous accuracy monitoring

## References

- Source code: `backend/app/services/emergency_detector.py`
- API endpoint: `POST /api/v1/emergency/analyze`
- Tests: `backend/tests/test_emergency_detector.py`, `backend/tests/test_emergency_api.py`
- Frontend: `frontend/src/components/EmergencyPanel.jsx`
- Schemas: `backend/app/schemas.py`
