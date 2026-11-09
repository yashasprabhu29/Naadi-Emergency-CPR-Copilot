# Naadi — AI-Powered Emergency Call-Taker Copilot

Naadi is a decision-support prototype for emergency call-takers handling multilingual callers. The project will transcribe Kannada, Kannada-English, Hindi and English audio, surface explainable emergency indicators, and provide human-reviewed prompts.

Naadi is not a medical device, an emergency service, or an integration with 108/112 infrastructure.

## Current Status

Completed milestones:
- **Milestone 01**: Gnani Prisma REST client with comprehensive error handling
- **Milestone 02**: FastAPI transcription endpoint with audio validation
- **Milestone 03**: React/Vite operator dashboard with real backend integration
- **Milestone 04**: Deterministic emergency detection engine
- **Milestone 04.1**: Detection engine hardening with structured utterances
- **Milestone 05**: Realtime streaming. The browser streams the microphone to `WS /api/v1/stream`, which relays 1,024-byte PCM frames to Gnani Prisma realtime STT. Detection reruns after every sentence and the console records time to flag.
- **Milestone 06**: Timbre CPR coaching. After the operator reviews a flag, the console plays a fixed, pre-written hands-only CPR instruction in Kannada, Hindi or English (Gnani Timbre v3.0), then a 110 per minute metronome with a live compression count. Prompts are cached in memory, so replays cost no credits.
- **Milestone 07**: SQLite call log. `Save call` stores the transcript, detection result, timings, ground-truth label and noise condition (`/api/v1/calls`). The Call log page reports arrests flagged, false flags and median time to flag on the labelled set, and exports CSV.

Not yet implemented: telephony (SIP/CTI) integration, clinician-reviewed scripts beyond the three launch languages, and user accounts.

### Things verified against the live Gnani API (9 Nov 2026)

- Realtime STT accepts exactly one `language_code` per session, even though the docs show lists. Live calls use the first code in `GNANI_LANGUAGE_CODE`, or `GNANI_STREAM_LANGUAGE_CODE` if set.
- Prisma v3.0 on realtime needs the `x-model` header; the relay sends both `model` and `x-model`.
- Timbre returns WAV with placeholder sizes (`0xFFFFFFFF`) in the header. The backend repairs the header before returning audio, and the upload validator measures real WAV length.

See [Milestone 04.1 Documentation](docs/milestone-04.1-detection-hardening.md) for detailed technical specifications.

## Emergency Detection

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
python -m backend.scripts.dev_server
```

The dev server reloads when backend code or `.env` changes, so a newly pasted `GNANI_API_KEY` takes effect without a restart. Saved calls go to `data/naadi.sqlite3` (ignored by Git); set `NAADI_DB_PATH` to move it. One live microphone session runs at a time (`STREAM_MAX_SESSIONS`), capped at 10 minutes (`STREAM_MAX_SECONDS`), to protect credits.

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

### Deploy on Render

The repo has a `Dockerfile` (builds the site, then runs FastAPI serving the site and API from one origin) and a `render.yaml` Blueprint.

1. In Render: **New > Blueprint**, connect this repository and choose the branch to deploy.
2. When asked, set `GNANI_API_KEY` (your Gnani key) and `NAADI_ACCESS_CODE` (a long code you give to judges and testers).
3. Create the Blueprint. The site is served at `https://<service-name>.onrender.com`.

Notes: the free plan sleeps after about 15 minutes idle (the first request then takes about 30 seconds), and the SQLite call log resets on each redeploy unless you attach a persistent disk and point `NAADI_DB_PATH` at it. Export the call log as CSV before redeploying. Daily caps (`NAADI_DAILY_*`) reset at midnight UTC and on restart.

To test the image locally: `docker build -t naadi .` then `docker run --env-file .env -e NAADI_ACCESS_CODE=test -p 10000:10000 naadi`, and open <http://localhost:10000>.

### Pages and hosting notes

- Routes: `/` (operator console), `/privacy` (privacy policy), `/terms` (terms and conditions). Any other path shows a 404 page.
- The routes use the browser path, so a static host must serve `index.html` for unknown paths (SPA fallback). Vite's dev and preview servers already do this.
- Contact email, team description and the "last updated" date for the legal pages live in `frontend/src/site.js`. Update the legal pages if data handling changes (for example, if transcripts are ever stored).
- Fonts (IBM Plex Sans and Mono, Noto Sans Kannada and Devanagari) are bundled from `@fontsource`, so the site makes no third-party requests.
- Icons live in `frontend/public`. After editing `favicon.svg`, regenerate the PNGs with `python frontend/scripts/render-icons.py` (needs PyMuPDF).
- When deploying, add the production origin to `CORS_ALLOWED_ORIGINS` on the backend.

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
- Sentence boundary detection uses simple regex splitting; may break on abbreviations.
- Speaker diarization requires manual annotation; automatic diarization not yet integrated.
- No audio denoising, AudioWorklet capture, WebSocket streaming, or SQLite storage exists yet.

See [Milestone 04.1 Known Limitations](docs/milestone-04.1-detection-hardening.md#known-limitations) for detailed analysis.

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

## Next milestones

Recommended priorities:

### Milestone 05: Gnani Prisma WebSocket Streaming (High Priority)
Replace REST API polling with real-time WebSocket streaming for live call transcription. See [Milestone 04.1 Next Steps](docs/milestone-04.1-detection-hardening.md#milestone-05-gnani-prisma-websocket-streaming-high-priority) for detailed specification.

**Key Features:**
- Real-time utterance streaming
- Sub-second detection latency
- Live operator dashboard updates

### Milestone 06: Advanced Negation & Temporal Reasoning (Medium Priority)
Implement sophisticated negation handling with contextual analysis and temporal reasoning.

### Other priorities:
1. Run authenticated live Prisma test with real Kannada-English recording
2. Add SQLite persistence for call records and detection history
3. Implement operator acknowledgment logging
4. Add Timbre text-to-speech for protocol prompts
