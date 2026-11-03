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
