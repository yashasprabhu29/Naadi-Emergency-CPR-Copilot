# Gnani Prisma REST integration

This milestone uses the official Gnani Speech API documentation available at:

- <https://docs.gnani.ai/api/STT/speech-to-text.md>
- <https://docs.gnani.ai/api/STT/models/prisma-v3.md>
- <https://docs.gnani.ai/api/STT/limits.md>
- <https://docs.gnani.ai/api/introduction/errors.md>

## Verified request

```text
POST https://api.vachana.ai/stt/v3
X-API-Key-ID: <GNANI_API_KEY>
Content-Type: multipart/form-data
```

The client sends these multipart fields by default:

```text
audio_file=<audio file>
model=prisma-v3.0
language_code=kn-IN,en-IN
format=codemix
```

Prisma v3.0 supports Kannada (`kn-IN`) and English (`en-IN`) and accepts one to four language hints. `codemix` keeps English words in Latin script while preserving the relevant native script.

REST accepts WAV, MP3, OGG, FLAC, AAC and M4A files up to 30 seconds. The service automatically converts input audio to 16 kHz mono. The local client checks WAV duration and leaves compressed-format duration enforcement to the API because no media decoder is included in this milestone.

## Response handling

The successful response is normalized into `TranscriptionResult` while preserving the original JSON body in `raw_response`. The client exposes transcript, request ID, model, detected language, processing time, end-to-end latency and the documented `truncated` flag.

## Error handling

The client recognizes the documented API error shapes and reports safe semantic codes for authentication failures, insufficient credits, permission errors, rate limits, invalid audio, server failures and malformed responses. Network and timeout errors are converted to local client errors. API credentials are never included in exception text or output.

## Live verification status

No live request has been made in this environment because `GNANI_API_KEY` is not configured and no private staged recording is present. The automated tests use `httpx.MockTransport` and do not consume Gnani credits.

## FastAPI upload endpoint

Milestone 02 exposes:

```text
POST /api/v1/transcriptions
```

Send one multipart form field named `audio`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/transcriptions \
  -F "audio=@recording.wav"
```

The endpoint accepts the documented extensions and matching audio media types, rejects empty and oversized files, validates WAV structure and duration, and uses a temporary file that is deleted after transcription. The default local upload limit is 25 MiB. The endpoint does not make a health-check request to Gnani.

Successful response fields mirror metadata actually returned by Prisma:

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

Fields absent from the upstream response are omitted from the JSON response. Error responses use a stable `success: false` envelope with an error code and safe message. Swagger documentation is available at `/docs` when FastAPI is running.
