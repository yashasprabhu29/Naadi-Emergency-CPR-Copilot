# Naadi — AI-Powered Emergency Call-Taker Copilot

Naadi is a decision-support prototype for emergency call-takers handling multilingual callers. The project will transcribe Kannada, Kannada-English, Hindi and English audio, surface explainable emergency indicators, and provide human-reviewed prompts.

Naadi is not a medical device, an emergency service, or an integration with 108/112 infrastructure.

## Milestone 04 status

This milestone adds a deterministic emergency indicator detection engine. The system uses explainable rule-based logic to identify potential cardiac-respiratory emergencies from multilingual transcripts. All emergency indicators require human operator review and confirmation.

Completed milestones:
- **Milestone 01**: Gnani Prisma REST client with comprehensive error handling
- **Milestone 02**: FastAPI transcription endpoint with audio validation
- **Milestone 03**: React/Vite operator dashboard with real backend integration
- **Milestone 04**: Deterministic emergency detection engine (current)

Not yet implemented: realtime audio streaming, SQLite persistence, or Timbre text-to-speech.

## Milestone 04 status

This milestone adds a deterministic, explainable emergency indicator detection engine. The engine applies rule-based pattern matching to identify potential cardiac-respiratory emergencies requiring immediate CPR protocol review.

**Detection Rule (RULE_001):**
A potential emergency indicator is raised when BOTH conditions are met within the latest three caller utterances:
1. At least one unresponsive indicator (unconscious, collapsed, not responding, etc.)
2. At least one abnormal breathing indicator (not breathing, gasping, breathing stopped, etc.)

**Supported languages:** Kannada, Hindi, English, and codemix variants.

**Important:** All detection results require human operator confirmation. The system does not use LLMs or probabilistic models. Contradictory evidence (negations, past tense, corrections) triggers review-required status instead of potential emergency.

## Prerequisites

- Python 3.13 or another supported Python 3.10+ installation.
- Internet access for installing dependencies and calling Gnani.
- A Gnani API key with STT access for live transcription.
- A staged audio file no longer than 30 seconds in WAV, MP3, OGG, FLAC, AAC or M4A format.

- Node.js 24+ and npm for the frontend.

## Environment setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows Git Bash
# .venv\Scripts\Activate.ps1   # Windows PowerShell

python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cp .env.example .env
```

Edit `.env` and set `GNANI_API_KEY`. The key is loaded only by the backend/CLI and is never sent to the frontend. `.env` is ignored by Git.

## Run tests

From the repository root:

```bash
source .venv/bin/activate
python -m pytest backend/tests -q
```

All external API calls in the test suite are mocked; tests do not need credentials or consume Gnani credits.

Frontend tests are run from `frontend` with `npm test`.

Build the frontend for production with `npm run build` from `frontend`.

## Run FastAPI

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload
```

Open Swagger at <http://127.0.0.1:8000/docs>.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

The response reports application metadata and whether `GNANI_API_KEY` is configured. It never returns the key.

The API health endpoint is also available at:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Upload a staged recording

After configuring `GNANI_API_KEY`, upload one supported recording:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/transcriptions \
  -F "audio=@audio/test_recordings/recording.wav"
```

Supported upload extensions and media types are WAV, MP3, OGG, FLAC, AAC and M4A. The default local upload limit is 25 MiB. Gnani REST accepts up to 30 seconds per request; WAV duration is checked locally, while compressed-file duration is checked by the upstream service.

Successful response example:

```json
{
  "success": true,
  "request_id": "request-id-from-gnani",
  "transcript": "ನನಗೆ chest pain ಇದೆ",
  "detected_language_code": "kn-IN",
  "model": "prisma-v3.0",
  "processing_time": 0.42,
  "end_to_end_latency": 0.55
}
```

Uploaded audio is written to a temporary file only while the request is processed and is deleted in a `finally` block. Credentials remain backend-only.

## Run the operator dashboard

Run FastAPI in one terminal and the dashboard in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>. Set `VITE_API_BASE_URL` in `frontend/.env` when the backend is not running at `http://127.0.0.1:8000`. The dashboard reads the real `/api/v1/health` response and sends uploads to `/api/v1/transcriptions`; it does not contain or request a Gnani API key. FastAPI explicitly allows the local Vite origins configured by `CORS_ALLOWED_ORIGINS`.

## Run a Prisma transcription

The CLI is located under `backend/scripts`:

```bash
source .venv/bin/activate
cd backend
python scripts/test_prisma.py --audio ../audio/test_recordings/recording.wav
```

The client sends this documented request to Gnani:

```text
POST https://api.vachana.ai/stt/v3
X-API-Key-ID: <local GNANI_API_KEY>
audio_file=<recording>
model=prisma-v3.0
language_code=kn-IN,en-IN
format=codemix
```

The CLI prints the transcript, detected language when returned, model, request ID and latency fields. It prints safe error messages for authentication, credit, permission, rate-limit, invalid audio, timeout and network failures.

## Audio validation

The client validates:

- File existence and regular-file status.
- Non-zero file size.
- Supported extension: `.wav`, `.mp3`, `.ogg`, `.flac`, `.aac`, `.m4a`.
- WAV duration when the standard library can inspect it.

For compressed formats, exact duration inspection is not available without an additional decoder; Gnani remains authoritative for the 30-second duration limit. Files longer than 30 seconds are rejected locally when WAV duration can be determined.

## Official Gnani references

- [Documentation index](https://docs.gnani.ai/llms.txt)
- [REST transcription](https://docs.gnani.ai/api/STT/speech-to-text.md)
- [Prisma v3.0](https://docs.gnani.ai/api/STT/models/prisma-v3.md)
- [STT limits](https://docs.gnani.ai/api/STT/limits.md)
- [Error reference](https://docs.gnani.ai/api/introduction/errors.md)

## Emergency detection

The emergency detection engine uses deterministic, explainable Python rules to identify potential cardiac-respiratory emergencies. It does not use LLMs or probabilistic models in the emergency decision path.

### Detection logic

**Core Rule (RULE_001):** A potential emergency indicator is raised when BOTH conditions are met within the latest three caller utterances:

1. At least one unresponsive indicator (unconscious, not responding, collapsed, fainted)
2. At least one abnormal breathing indicator (not breathing, no normal breathing, gasping)

### Supported phrases

The detector recognizes emergency phrases in Kannada, Hindi, and English:

**Unresponsive indicators:**
- Kannada: ಎಚ್ಚರ ಇಲ್ಲ, ಎಚ್ಚರ ತಪ್ಪಿ, ಮಾತಾಡ್ತಿಲ್ಲ, ಸ್ಪಂದಿಸ್ತಿಲ್ಲ, ಬಿದ್ದುಬಿಟ್ರು
- Hindi: बेहोश, होश नहीं, जवाब नहीं, गिर गए
- English: unconscious, not responding, collapsed, fainted, unresponsive

**Abnormal breathing indicators:**
- Kannada: ಉಸಿರಾಡ್ತಿಲ್ಲ, ಉಸಿರು ಇಲ್ಲ, ಉಸಿರು ನಿಂತಿದೆ
- Hindi: साँस नहीं, सांस रुक गई
- English: not breathing, no normal breathing, gasping, stopped breathing

Matching is case-insensitive and works across mixed-language utterances.

### Contradiction handling

The detector identifies contradictory evidence including:
- Negation phrases: "is breathing", "breathing normally", "is awake", "responding now"
- Past tense indicators: "was unconscious", "earlier", "before"
- Caller corrections: "Wait, he is breathing now"

When contradictions are detected, the status changes from `potential_emergency` to `review_required`.

### Detection statuses

- **no_indicator**: No emergency phrases detected
- **review_required**: Single indicator or contradictory evidence present
- **potential_emergency**: Both indicators present without contradictions

All non-zero detections require explicit operator confirmation.

### API endpoint

```bash
curl -X POST http://127.0.0.1:8000/api/v1/emergency/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "utterances": [
      {"text": "He is unconscious", "speaker": "caller", "utterance_index": 0},
      {"text": "He is not breathing", "speaker": "caller", "utterance_index": 1}
    ]
  }'
```

Response includes matched indicators, explanations, rule identifiers, contradictory evidence, and uncertainty notes.

### Medical disclaimer

This system provides decision support only. It does not:
- Diagnose medical conditions
- Authorize ambulance dispatch
- Replace trained emergency operators
- Guarantee detection accuracy
- Connect to 108/112 emergency infrastructure

All emergency indicators require human review and confirmation.

## Current limitations

- No live API transcription has been run because no `GNANI_API_KEY` is configured in this environment.
- No staged recording is included in the repository; private recordings are intentionally ignored.
- REST is limited to 30 seconds per request by the documented API.
- Compressed-file duration cannot be inspected locally without an additional media decoder; the upstream API enforces its duration limit.
- Emergency detection analyzes the full transcript as a single utterance; structured multi-utterance input would improve accuracy.
- No audio denoising, AudioWorklet capture, WebSocket streaming, or SQLite storage exists yet.

## Error handling

The upload endpoint returns a stable envelope:

```json
{
  "success": false,
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Content type 'text/plain' is not valid for .wav."
  }
}
```

It handles missing credentials, invalid or empty audio, unsupported media, oversized uploads, documented Gnani authentication/credit/scope/rate-limit/server errors, timeouts, network failures and malformed upstream responses without returning stack traces or secrets.

## Testing

### Backend tests

```bash
source .venv/bin/activate
python -m pytest backend/tests -v
```

Test coverage:
- 13 Prisma client tests (validation, HTTP errors, timeouts)
- 20 transcription API tests (uploads, CORS, error handling)
- 24 emergency detector tests (phrase detection, contradictions, languages)
- 16 emergency API tests (endpoint behavior, validation, schemas)

**Total: 73 backend tests**

All external API calls are mocked; tests do not consume Gnani credits.

### Frontend tests

```bash
cd frontend
npm test
```

**Total: 11 frontend tests** covering API integration, uploads, validation, and error handling.

### Production build

```bash
cd frontend
npm run build
```

## Next milestone

Priority tasks:
1. Run authenticated live Prisma test with real Kannada-English recording
2. Improve emergency detection with structured multi-utterance transcripts
3. Add SQLite persistence for call records and detection history
4. Implement operator acknowledgment logging
5. Add Timbre text-to-speech for protocol prompts
