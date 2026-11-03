# Naadi — AI-Powered Emergency Call-Taker Copilot

Naadi is a decision-support prototype for emergency call-takers handling multilingual callers. The project will transcribe Kannada, Kannada-English, Hindi and English audio, surface explainable emergency indicators, and provide human-reviewed prompts.

Naadi is not a medical device, an emergency service, or an integration with 108/112 infrastructure.

## Milestone 02 status

This milestone adds a FastAPI staged-audio upload endpoint on top of the initial backend foundation and standalone Gnani Prisma REST transcription client. It does not include the React frontend, realtime audio streaming, SQLite persistence, emergency rules, or Timbre text-to-speech.

The immediate live objective is to transcribe a staged Kannada-English recording with Gnani Prisma v3.0.

## Prerequisites

- Python 3.13 or another supported Python 3.10+ installation.
- Internet access for installing dependencies and calling Gnani.
- A Gnani API key with STT access for live transcription.
- A staged audio file no longer than 30 seconds in WAV, MP3, OGG, FLAC, AAC or M4A format.

The current implementation does not require Node.js because React is planned for a later milestone.

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

## Current limitations

- No live API transcription has been run because no `GNANI_API_KEY` is configured in this environment.
- No staged recording is included in the repository; private recordings are intentionally ignored.
- REST is limited to 30 seconds per request by the documented API.
- Compressed-file duration cannot be inspected locally without an additional media decoder; the upstream API enforces its duration limit.
- No audio denoising, AudioWorklet capture, WebSocket streaming, React interface, SQLite storage, emergency rules or Timbre integration exists yet.

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

## Next milestone

Run the authenticated Prisma REST smoke test through both the CLI and `/api/v1/transcriptions` using a real staged Kannada-English recording. Then add the first minimal operator-facing frontend.
