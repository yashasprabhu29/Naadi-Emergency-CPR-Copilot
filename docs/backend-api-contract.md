# Naadi Backend API Contract

**Version:** 1.0  
**Date:** November 8, 2026  
**Backend Version:** 0.1.0 (Milestone 04.1 + TTS)

This document defines the complete HTTP API contract for the Naadi Emergency CPR Copilot backend. All endpoints are served by FastAPI and documented interactively at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Base Configuration

**Base URL:** `http://localhost:8000` (development)  
**API Prefix:** `/api/v1`  
**Protocol:** HTTP/1.1  
**Content Types:** `application/json`, `multipart/form-data`, `audio/wav`

### CORS Policy

**Allowed Origins:**
- `http://localhost:5173`
- `http://127.0.0.1:5173`

**Allowed Methods:** `GET`, `POST`, `OPTIONS`  
**Allowed Headers:** `Content-Type`, `Accept`

---

## Health Endpoints

### `GET /`

**Description:** Root health check  
**Authentication:** None

**Response:** `200 OK`
```json
{
  "message": "Naadi Emergency CPR Copilot",
  "version": "0.1.0",
  "status": "ok"
}
```

### `GET /health`

**Description:** Service health check  
**Authentication:** None

**Response:** `200 OK`
```json
{
  "status": "ok"
}
```

### `GET /api/v1/health`

**Description:** API health with configuration status  
**Authentication:** None

**Response:** `200 OK`
```json
{
  "status": "ok",
  "gnani_api_key_configured": true,
  "version": "0.1.0"
}
```

---

## Transcription Endpoint

### `POST /api/v1/transcriptions`

**Description:** Upload audio and receive Prisma v3.0 transcription  
**Authentication:** None (backend uses configured `GNANI_API_KEY`)  
**Content-Type:** `multipart/form-data`

#### Request

**Form Field:**
- `audio` (required): Audio file

**Supported Formats:**
- `.wav` (PCM, max 30 seconds when inspectable)
- `.mp3` (max 30 seconds, enforced by Gnani)
- `.flac` (max 30 seconds, enforced by Gnani)
- `.ogg` (max 30 seconds, enforced by Gnani)
- `.aac` (max 30 seconds, enforced by Gnani)
- `.m4a` (max 30 seconds, enforced by Gnani)

**Constraints:**
- Maximum file size: 25 MB (configurable via `MAX_UPLOAD_SIZE_BYTES`)
- Audio must be non-empty
- MIME type must match file extension

#### Responses

**Success:** `200 OK`
```json
{
  "success": true,
  "request_id": "req_abc123",
  "transcript": "ನನಗೆ chest pain ಇದೆ",
  "detected_language_code": "kn-IN",
  "model": "prisma-v3.0",
  "processing_time": 0.42,
  "end_to_end_latency": 0.55,
  "truncated": false
}
```

**Field Descriptions:**
- `success`: Always `true` for successful transcription
- `request_id`: Gnani request identifier (if provided)
- `transcript`: Transcribed text (code-mixed format)
- `detected_language_code`: Primary detected language
- `model`: Model used (always `prisma-v3.0`)
- `processing_time`: Gnani processing time in seconds (if provided)
- `end_to_end_latency`: Total API latency in seconds (if provided)
- `truncated`: Whether audio was truncated by Gnani

**Error Responses:**

`400 Bad Request` - Invalid audio file
```json
{
  "success": false,
  "error_code": "INVALID_AUDIO",
  "message": "WAV file could not be parsed: invalid header"
}
```

`413 Request Entity Too Large` - File too large
```json
{
  "success": false,
  "error_code": "FILE_TOO_LARGE",
  "message": "Upload exceeds maximum allowed size of 25 MB"
}
```

`415 Unsupported Media Type` - Invalid file type
```json
{
  "success": false,
  "error_code": "UNSUPPORTED_FORMAT",
  "message": "Unsupported audio extension '.txt'. Supported: .wav, .mp3, .flac, .ogg, .aac, .m4a"
}
```

`503 Service Unavailable` - API key not configured
```json
{
  "success": false,
  "error_code": "SERVICE_UNAVAILABLE",
  "message": "GNANI_API_KEY is not configured"
}
```

**Upstream Error Pass-through:**

`401 Unauthorized` - Invalid Gnani API key
```json
{
  "success": false,
  "error_code": "INVALID_API_KEY",
  "message": "Gnani authentication failed"
}
```

`402 Payment Required` - Insufficient Gnani credits
```json
{
  "success": false,
  "error_code": "INSUFFICIENT_CREDIT",
  "message": "Gnani account has insufficient credits"
}
```

`403 Forbidden` - STT scope not enabled
```json
{
  "success": false,
  "error_code": "SCOPE_NOT_ALLOWED",
  "message": "Gnani API key lacks STT permission"
}
```

`429 Too Many Requests` - Rate limited by Gnani
```json
{
  "success": false,
  "error_code": "RATE_LIMITED",
  "message": "Gnani rate limit exceeded"
}
```

`502 Bad Gateway` - Network error
```json
{
  "success": false,
  "error_code": "UPSTREAM_ERROR",
  "message": "Could not reach Gnani service"
}
```

`504 Gateway Timeout` - Gnani timeout
```json
{
  "success": false,
  "error_code": "TIMEOUT",
  "message": "Gnani request timed out"
}
```

---

## Emergency Analysis Endpoint

### `POST /api/v1/emergency/analyze`

**Description:** Analyze transcript utterances for cardiac arrest indicators  
**Authentication:** None  
**Content-Type:** `application/json`

#### Request

```json
{
  "utterances": [
    {
      "id": "utt_001",
      "text": "He is not responding",
      "speaker": "caller",
      "timestamp": 1699468800.0,
      "language": "en-IN",
      "confidence": 0.95
    },
    {
      "id": "utt_002",
      "text": "Is he breathing?",
      "speaker": "operator",
      "timestamp": 1699468805.0,
      "language": "en-IN",
      "confidence": 0.98
    },
    {
      "id": "utt_003",
      "text": "No, he is not breathing",
      "speaker": "caller",
      "timestamp": 1699468808.0,
      "language": "en-IN",
      "confidence": 0.96
    }
  ]
}
```

**Utterance Schema:**
- `id` (optional): Unique identifier for traceability
- `text` (required): Utterance text (any language)
- `speaker` (required): Speaker role - must be `"caller"`, `"operator"`, or `"unknown"`
- `timestamp` (optional): Unix timestamp
- `language` (optional): ISO language code
- `confidence` (optional): Transcription confidence (0.0-1.0)

**Rules:**
- Only `speaker="caller"` utterances are analyzed
- Operator and unknown speakers are explicitly excluded
- Empty or whitespace-only text is rejected
- Detection uses a 3-utterance sliding window
- Supports Kannada, Hindi, and English phrases

#### Response

**Success:** `200 OK`

**Potential Emergency:**
```json
{
  "status": "POTENTIAL_EMERGENCY",
  "requires_operator_confirmation": true,
  "unresponsive": true,
  "abnormal_breathing": true,
  "contradictions": [],
  "detected_phrases": [
    {
      "phrase": "not responding",
      "category": "unresponsive",
      "utterance_id": "utt_001"
    },
    {
      "phrase": "not breathing",
      "category": "abnormal_breathing",
      "utterance_id": "utt_003"
    }
  ],
  "explanation": "Both cardiac arrest indicators detected within 3-utterance window",
  "detector_version": "1.1.0"
}
```

**Review Required:**
```json
{
  "status": "REVIEW_REQUIRED",
  "requires_operator_confirmation": true,
  "unresponsive": true,
  "abnormal_breathing": false,
  "contradictions": [],
  "detected_phrases": [
    {
      "phrase": "not waking up",
      "category": "unresponsive",
      "utterance_id": "utt_001"
    }
  ],
  "explanation": "Single indicator detected: operator review required",
  "detector_version": "1.1.0"
}
```

**No Indicator:**
```json
{
  "status": "NO_INDICATOR",
  "requires_operator_confirmation": false,
  "unresponsive": false,
  "abnormal_breathing": false,
  "contradictions": [],
  "detected_phrases": [],
  "explanation": "No cardiac arrest indicators detected in caller utterances",
  "detector_version": "1.1.0"
}
```

**Response Fields:**
- `status`: Detection result - `"POTENTIAL_EMERGENCY"`, `"REVIEW_REQUIRED"`, or `"NO_INDICATOR"`
- `requires_operator_confirmation`: Always `true` when indicators present
- `unresponsive`: Whether unresponsiveness detected
- `abnormal_breathing`: Whether abnormal breathing detected
- `contradictions`: List of negation/contradiction phrases found
- `detected_phrases`: Array of matched emergency phrases with metadata
- `explanation`: Human-readable detection summary
- `detector_version`: Detection engine version

**Detection Statuses:**
- `POTENTIAL_EMERGENCY`: Both unresponsiveness AND abnormal breathing detected within 3-utterance window
- `REVIEW_REQUIRED`: Only one indicator detected, or contradictions present
- `NO_INDICATOR`: No emergency indicators in caller speech

**Error Responses:**

`400 Bad Request` - Invalid request
```json
{
  "detail": "utterances: Field required"
}
```

`422 Unprocessable Entity` - Validation error
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "utterances", 0, "text"],
      "msg": "Input should be a valid string"
    }
  ]
}
```

---

## TTS Endpoints

### `GET /api/v1/tts/prompts`

**Description:** List available emergency coaching prompts  
**Authentication:** None

**Response:** `200 OK`
```json
{
  "prompts": {
    "start_cpr_kannada": {
      "language": "kn-IN",
      "description": "Start CPR instructions in Kannada"
    },
    "start_cpr_hindi": {
      "language": "hi-IN",
      "description": "Start CPR instructions in Hindi"
    },
    "start_cpr_english": {
      "language": "en-IN",
      "description": "Start CPR instructions in English"
    },
    "check_breathing_kannada": {
      "language": "kn-IN",
      "description": "Check breathing in Kannada"
    },
    "check_breathing_hindi": {
      "language": "hi-IN",
      "description": "Check breathing in Hindi"
    },
    "check_breathing_english": {
      "language": "en-IN",
      "description": "Check breathing in English"
    }
  }
}
```

### `POST /api/v1/tts/synthesize`

**Description:** Synthesize emergency prompt to audio  
**Authentication:** None (backend uses configured `GNANI_API_KEY`)  
**Content-Type:** `application/json`

#### Request

```json
{
  "prompt_id": "start_cpr_kannada",
  "speed": 1.0
}
```

**Fields:**
- `prompt_id` (required): Prompt identifier from `/api/v1/tts/prompts`
- `speed` (optional): Playback speed (0.85-1.15, default: 1.0)

#### Response

**Success:** `200 OK`  
**Content-Type:** `audio/wav`

Binary WAV audio file (48kHz, mono, 16-bit PCM)

**Error Responses:**

`400 Bad Request` - Invalid prompt
```json
{
  "success": false,
  "error_code": "INVALID_PROMPT",
  "message": "Unknown prompt_id 'invalid'. Available: start_cpr_kannada, ..."
}
```

`503 Service Unavailable` - API key not configured
```json
{
  "success": false,
  "error_code": "SERVICE_UNAVAILABLE",
  "message": "GNANI_API_KEY is not configured"
}
```

**Upstream Error Pass-through:**

`401 Unauthorized` - Invalid Gnani API key
```json
{
  "success": false,
  "error_code": "INVALID_API_KEY",
  "message": "Gnani authentication failed"
}
```

`429 Too Many Requests` - Rate limited
```json
{
  "success": false,
  "error_code": "RATE_LIMITED",
  "message": "Gnani rate limit exceeded"
}
```

---

## Emergency Detection Rules

### Supported Languages

- **Kannada (kn-IN):** Primary language, native script supported
- **Hindi (hi-IN):** Secondary language, Devanagari script supported
- **English (en-IN):** Code-mixed and standalone English

### Unresponsiveness Indicators

**English:**
- not responding, unresponsive, not waking, unconscious, fainted, collapsed, passed out

**Kannada:**
- ಪ್ರತಿಕ್ರಿಯಿಸುತ್ತಿಲ್ಲ, ಪ್ರಜ್ಞೆ ಇಲ್ಲ, ಎಚ್ಚರವಾಗುತ್ತಿಲ್ಲ, ಸರಿಯಾಗಿಲ್ಲ

**Hindi:**
- प्रतिक्रिया नहीं, होश नहीं, जाग नहीं रहा

### Abnormal Breathing Indicators

**English:**
- not breathing, no breath, gasping, gurgling, snoring, struggling to breathe

**Kannada:**
- ಉಸಿರಾಡುತ್ತಿಲ್ಲ, ಉಸಿರಾಟ ಇಲ್ಲ, ಉಸಿರು ಇಲ್ಲ

**Hindi:**
- सांस नहीं, सांस लेने में, सांस रुका

### Negation Detection

Detected patterns automatically create contradictions:
- English: "no", "not", "never", "was", "were", "used to"
- Kannada: "ಅಲ್ಲ", "ಇಲ್ಲ", "ಇರಲಿಲ್ಲ"
- Hindi: "नहीं था", "नहीं थी"

### Detection Algorithm

1. **Speaker Filtering:** Only `speaker="caller"` utterances analyzed
2. **Sliding Window:** 3-utterance window for temporal proximity
3. **Unicode Normalization:** NFC normalization for Kannada/Hindi
4. **Case Insensitive:** English matching is case-insensitive
5. **Duplicate Prevention:** Same phrase in same utterance counted once
6. **Contradiction Detection:** Negation phrases reduce confidence

**Status Logic:**
- `POTENTIAL_EMERGENCY`: Both indicators within window, no contradictions
- `REVIEW_REQUIRED`: Single indicator OR contradictions present
- `NO_INDICATOR`: No indicators detected

---

## Configuration Requirements

### Environment Variables

**Required:**
```bash
GNANI_API_KEY=<your-gnani-api-key>
```

**Optional:**
```bash
GNANI_BASE_URL=https://api.vachana.ai
GNANI_STT_PATH=/stt/v3
GNANI_MODEL=prisma-v3.0
GNANI_LANGUAGE_CODE=kn-IN,en-IN
GNANI_FORMAT=codemix
GNANI_TIMEOUT_SECONDS=60
MAX_UPLOAD_SIZE_BYTES=26214400
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Gnani API Requirements

**API Key Scopes:**
- ✓ Speech-to-Text (STT)
- ✓ Text-to-Speech (TTS)

**Authentication:** `X-API-Key-ID` header  
**Endpoints:**
- STT: `POST https://api.vachana.ai/stt/v3`
- TTS: `POST https://api.vachana.ai/api/v1/tts/inference`

---

## Integration Examples

### Upload Audio (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/transcriptions \
  -F "audio=@recording.wav"
```

### Upload Audio (JavaScript)

```javascript
const formData = new FormData();
formData.append('audio', audioFile);

const response = await fetch('http://localhost:8000/api/v1/transcriptions', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result.transcript);
```

### Analyze Emergency

```javascript
const response = await fetch('http://localhost:8000/api/v1/emergency/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    utterances: [
      {
        id: 'utt_1',
        text: 'He is not responding',
        speaker: 'caller',
        timestamp: Date.now() / 1000
      },
      {
        id: 'utt_2',
        text: 'Not breathing',
        speaker: 'caller',
        timestamp: Date.now() / 1000
      }
    ]
  })
});

const analysis = await response.json();
if (analysis.status === 'POTENTIAL_EMERGENCY') {
  console.log('Emergency detected!');
}
```

### Synthesize TTS Prompt

```javascript
const response = await fetch('http://localhost:8000/api/v1/tts/synthesize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt_id: 'start_cpr_kannada',
    speed: 1.0
  })
});

const audioBlob = await response.blob();
const audio = new Audio(URL.createObjectURL(audioBlob));
audio.play();
```

---

## OpenAPI Documentation

**Interactive API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Error Handling Strategy

### Client Errors (4xx)

- **400:** Validation failures, malformed requests
- **413:** File size exceeded
- **415:** Unsupported media type
- **422:** Pydantic validation errors (FastAPI default)

### Server Errors (5xx)

- **500:** Unexpected internal errors
- **502:** Upstream service unreachable
- **503:** Service unavailable (missing configuration)
- **504:** Upstream timeout

### Error Response Schema

All error responses follow a consistent structure:

```json
{
  "success": false,
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message"
}
```

---

## Testing

### Health Check

```bash
curl http://localhost:8000/health
```

### Upload Test Audio

```bash
curl -X POST http://localhost:8000/api/v1/transcriptions \
  -F "audio=@test.wav" \
  | jq .
```

### Test Emergency Detection

```bash
curl -X POST http://localhost:8000/api/v1/emergency/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "utterances": [
      {"text": "not responding", "speaker": "caller"},
      {"text": "not breathing", "speaker": "caller"}
    ]
  }' \
  | jq .
```

---

## Changelog

### Version 1.0 (November 8, 2026)

- Initial API contract
- Prisma v3.0 STT integration
- Timbre v3.0 TTS integration
- Emergency detection v1.1.0
- Structured utterance support
- Multi-language detection (Kannada, Hindi, English)

---

**End of API Contract**
