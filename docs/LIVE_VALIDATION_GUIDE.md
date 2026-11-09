# Naadi Backend Live Validation Guide

This guide explains how to perform live validation of the Gnani Prisma STT integration once you have a staged test audio recording.

## Prerequisites

✅ Backend implementation complete  
✅ GNANI_API_KEY configured in root `.env`  
✅ Virtual environment activated  
✅ All 117 backend tests passing  

## What You Need

### Test Audio Recording

**Requirements:**
- **Content:** Fictional emergency scenario
  - Example: "He is not responding. He is not breathing."
  - Kannada: "ಅವನು ಪ್ರತಿಕ್ರಿಯಿಸುತ್ತಿಲ್ಲ. ಅವನು ಉಸಿರಾಡುತ್ತಿಲ್ಲ."
  - Hindi: "वह प्रतिक्रिया नहीं दे रहा है। वह सांस नहीं ले रहा है।"
- **Duration:** ≤30 seconds (Gnani REST API limit)
- **Format:** WAV (recommended), MP3, FLAC, OGG, AAC, or M4A
- **Source:** Staged demonstration only (NEVER a real emergency call)
- **Language:** Kannada, Kannada-English codemix, or Hindi preferred

### ⚠️ Important Safety Guidelines

**DO:**
- ✅ Use fictional scenarios only
- ✅ Stage recordings with consenting participants
- ✅ Use made-up names and situations
- ✅ Keep recordings under 30 seconds

**DO NOT:**
- ❌ Use real emergency calls
- ❌ Use recordings with real patient information
- ❌ Record actual medical emergencies
- ❌ Use any confidential or sensitive recordings

## Step-by-Step Validation

### Step 1: Prepare Audio File

Place your test audio in the designated directory:

```bash
# Create directory if needed (should already exist)
mkdir -p "audio/test_recordings"

# Copy or move your test audio
# Example: test.wav, demo.mp3, sample.flac
```

**File location:**
```
d:\Naadi – Emergency CPR Copilot\audio\test_recordings\test.wav
```

### Step 2: Verify Environment

```powershell
cd "d:\Naadi – Emergency CPR Copilot"

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Verify API key is configured (should show "yes")
python -c "from backend.app.config import get_settings; print('API key configured:', get_settings().has_gnani_api_key)"
```

Expected output:
```
API key configured: True
```

### Step 3: Run Live Validation

```powershell
cd backend
python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/test.wav
```

### Step 4: Interpret Results

#### ✅ Success Output

```
======================================================================
PRISMA v3.0 STT LIVE VERIFICATION
======================================================================

Test audio: test.wav
File size: 245,832 bytes

📤 Sending to Gnani Prisma v3.0...

✓ SUCCESS

Latency: 2.456s

Transcript:
  ಅವನು ಪ್ರತಿಕ್ರಿಯಿಸುತ್ತಿಲ್ಲ. ಅವನು ಉಸಿರಾಡುತ್ತಿಲ್ಲ.

Metadata:
  Request ID: req_abc123
  Model: prisma-v3.0
  Detected Language: kn-IN
  Processing Time: 0.423s
  E2E Latency: 0.512s
  Truncated: False

--- Verification Summary ---
✓ Authentication: SUCCESS
✓ Request: SUCCESS
✓ Response parsing: SUCCESS
✓ Transcript received: 82 characters
✓ Language detection: kn-IN
```

**What to Check:**
1. ✅ Authentication succeeded
2. ✅ Transcript matches your audio content
3. ✅ Language detection is correct (kn-IN, hi-IN, en-IN)
4. ✅ Latency is reasonable (typically 1-5 seconds)
5. ✅ No truncation warning

#### ❌ Error: Authentication Failed

```
❌ FAILED: PrismaAPIError
   Gnani Prisma error (401, INVALID_API_KEY): Unauthorized

--- Verification Summary ---
❌ Authentication: FAILED
   Check API key is valid and has STT scope
```

**Fix:**
1. Verify GNANI_API_KEY in `.env` is correct
2. Check API key hasn't expired
3. Confirm STT scope is enabled in Gnani dashboard
4. Ensure no extra whitespace in `.env` file

#### ❌ Error: Audio Validation Failed

```
❌ FAILED: AudioValidationError
   WAV duration is 45.23s; Prisma REST accepts at most 30s per request.

--- Verification Summary ---
❌ Audio validation: FAILED
   Check audio format and duration
```

**Fix:**
1. Trim audio to ≤30 seconds
2. Verify file format is supported
3. Check file isn't corrupted

#### ❌ Error: Scope Not Allowed

```
❌ FAILED: PrismaAPIError
   Gnani Prisma error (403, SCOPE_NOT_ALLOWED): Permission denied

--- Verification Summary ---
❌ Permission: FAILED
   Enable STT scope in Gnani dashboard
```

**Fix:**
1. Log into Gnani dashboard
2. Navigate to API keys
3. Enable "Speech-to-Text" scope
4. Save and retry

## Testing Multiple Audio Files

```powershell
# Test multiple files in sequence
cd backend

# English
python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/english.wav

# Kannada
python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/kannada.wav

# Hindi
python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/hindi.wav

# Codemix
python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/codemix.wav
```

## What Gets Validated

✅ **Authentication:** API key is valid and has STT scope  
✅ **Request Format:** Multipart form-data with correct headers  
✅ **Audio Validation:** File format, size, duration checks  
✅ **Response Parsing:** JSON structure and field extraction  
✅ **Transcription Quality:** Actual text returned by provider  
✅ **Language Detection:** Kannada (kn-IN), Hindi (hi-IN), English (en-IN)  
✅ **Metadata Extraction:** Request ID, model, latency, truncation flag  
✅ **Error Handling:** Provider errors correctly surfaced  

## After Validation

### If Successful ✅

1. Document results in your notes:
   - Transcript accuracy for each language
   - Average latency
   - Any language detection issues
   - Any unexpected truncation

2. Test emergency detection with real transcript:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/emergency/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "utterances": [
         {"text": "[paste actual transcript]", "speaker": "caller"}
       ]
     }'
   ```

3. Mark live validation as complete ✅

### If Issues Found ❌

1. Note exact error message and status code
2. Verify prerequisites (API key, file format, duration)
3. Try alternative audio file to isolate issue
4. Check Gnani service status
5. Review error handling in `backend/app/services/prisma_client.py`

## Common Issues and Solutions

### Issue: "Cannot reach Gnani service"

**Cause:** Network connectivity issue  
**Fix:**
1. Check internet connection
2. Verify firewall isn't blocking HTTPS to api.vachana.ai
3. Try again after a moment

### Issue: "Gnani returned invalid JSON"

**Cause:** Malformed provider response  
**Fix:**
1. Check Gnani service status
2. Verify API endpoint hasn't changed
3. Report to Gnani support if persistent

### Issue: "WAV file could not be parsed"

**Cause:** Corrupted or invalid WAV file  
**Fix:**
1. Re-record or re-encode audio
2. Verify WAV format with: `ffmpeg -i file.wav`
3. Try converting to standard format: `ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav`

### Issue: Rate Limiting (429)

**Cause:** Too many requests to Gnani API  
**Fix:**
1. Wait 60 seconds
2. Reduce request frequency
3. Check account rate limits in dashboard

## Next Steps After Live Validation

Once Prisma STT is validated:

1. ✅ Update project status: Live STT validation complete
2. ✅ Document transcript quality in your notes
3. ✅ Test complete workflow: Audio → STT → Detection → TTS
4. ✅ Verify emergency detection with real transcripts
5. ✅ Backend freeze complete
6. 🎯 Begin frontend redesign with frozen backend API

---

**Questions or Issues?**

- Check `docs/backend-api-contract.md` for API details
- Review `docs/gnani-prisma-rest.md` for Prisma specifics
- See `GNANI_API_SETUP.md` for configuration help

**Backend Status:** Ready for live validation  
**Required:** Staged test audio in `audio/test_recordings/`
