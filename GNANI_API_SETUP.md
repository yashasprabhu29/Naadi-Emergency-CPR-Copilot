# Gnani API Integration Setup Guide

This guide helps you configure and validate your Gnani API key for **Naadi – Emergency CPR Copilot**.

## Prerequisites

✅ You have a Gnani API key with **STT (Speech-to-Text)** and **TTS (Text-to-Speech)** scopes enabled  
✅ Python virtual environment is activated (`.venv`)  
✅ All dependencies are installed (`pip install -r backend/requirements.txt`)

---

## Step 1: Configure API Key Securely

### Create `.env` file

```powershell
# Copy the example template
Copy-Item .env.example .env
```

### Edit `.env` file

Open `.env` in your text editor and set:

```ini
GNANI_API_KEY=<paste-your-actual-key-here>
```

**IMPORTANT:**
- ❌ **NEVER commit** `.env` to git
- ❌ **NEVER share** your API key
- ✅ `.env` is already in `.gitignore`
- ✅ Only `.env.example` (without the key) should be committed

### Verify `.env` is ignored by git

```powershell
git check-ignore .env
```

Expected output: `.env` (confirms it's ignored)

---

## Step 2: Verify Configuration

### Check health endpoint (no API call)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start backend
cd backend
uvicorn app.main:app --reload
```

In another terminal:

```powershell
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "Naadi",
  "version": "0.1.0",
  "gnani_api_key_configured": true,  ← Should be true
  "prisma_model": "prisma-v3.0"
}
```

---

## Step 3: Test Live API Integration

### Run live API test script

```powershell
# From project root (with .venv activated)
python backend/scripts/test_live_api.py
```

This script will:

1. ✅ Verify API key is configured
2. 📤 Test **Prisma STT** (if test audio available)
3. 📤 Test **Timbre TTS** with emergency prompts
4. 💾 Save generated audio to `audio/prompts/`

**Note:** This script makes **REAL API calls** and consumes credits.

### Expected output

```
======================================================================
  API KEY CONFIGURATION CHECK
======================================================================
✓ GNANI_API_KEY is configured
✓ Base URL: https://api.vachana.ai
✓ Model: prisma-v3.0
✓ Language: kn-IN,en-IN
✓ Format: codemix

======================================================================
  TIMBRE TTS TEST - Emergency Prompts
======================================================================
✓ Available prompts: 6
  - start_cpr_kannada              [kn-IN] Start CPR instructions in Kannada
  - start_cpr_hindi                [hi-IN] Start CPR instructions in Hindi
  - start_cpr_english              [en-IN] Start CPR instructions in English
  ...

📤 Synthesizing: start_cpr_kannada
✓ SUCCESS - Generated in 0.95s
   Audio size: 89,644 bytes
   Content type: audio/wav
   Duration: ~2.50s
   Saved to: audio\prompts\test_cpr_kannada.wav

✓ 3/3 TTS tests passed
```

---

## Step 4: Test STT with Your Own Audio (Optional)

### Add test recording

Place a short (≤30s) audio file in `audio/test_recordings/`:

```
audio/test_recordings/my_test.wav
```

Supported formats: `.wav`, `.mp3`, `.ogg`, `.flac`, `.aac`, `.m4a`

**IMPORTANT:**
- ⚠ Use **fictional emergency scenarios only**
- ⚠ **NEVER call actual 108 or 112 numbers**
- ⚠ Use **consenting participants only**
- ⚠ Keep recordings **≤30 seconds** (REST API limit)

### Run test again

```powershell
python backend/scripts/test_live_api.py
```

The script will automatically detect and transcribe your audio file.

---

## Configuration Reference

All settings are in `.env` (see `.env.example` for defaults):

```ini
# Required
GNANI_API_KEY=your_api_key_here

# Optional (defaults work for competition demo)
GNANI_BASE_URL=https://api.vachana.ai
GNANI_STT_PATH=/stt/v3
GNANI_MODEL=prisma-v3.0
GNANI_LANGUAGE_CODE=kn-IN,en-IN  # Kannada + English
GNANI_FORMAT=codemix              # English in Latin, Kannada in Kannada script
GNANI_TIMEOUT_SECONDS=60
MAX_UPLOAD_SIZE_BYTES=26214400    # 25 MiB
```

---

## Troubleshooting

### "GNANI_API_KEY is not configured"

**Problem:** `.env` file missing or empty key  
**Solution:**
1. Verify `.env` exists: `Test-Path .env`
2. Check key is set: `Get-Content .env | Select-String GNANI_API_KEY`
3. Ensure no extra spaces around `=`

### "401 INVALID_API_KEY"

**Problem:** API key is incorrect or invalid  
**Solution:**
1. Double-check key was copied correctly (no extra spaces/newlines)
2. Verify key has not expired
3. Check key has **STT and TTS scopes** enabled in Gnani dashboard

### "403 SCOPE_NOT_ALLOWED"

**Problem:** API key lacks STT or TTS permissions  
**Solution:** Contact Gnani support to enable required scopes

### "429 RATE_LIMITED"

**Problem:** Too many requests (account limit)  
**Solution:**
1. Wait a few seconds before retrying
2. Check your account's concurrent request limit
3. For testing, use mocked tests instead of live API

### "Timeout / Network error"

**Problem:** Cannot reach Gnani API  
**Solution:**
1. Check internet connection
2. Verify firewall allows HTTPS to `api.vachana.ai`
3. Increase timeout: `GNANI_TIMEOUT_SECONDS=120` in `.env`

---

## API Endpoints Used

### Prisma STT (Speech-to-Text)

- **URL:** `POST https://api.vachana.ai/stt/v3`
- **Model:** `prisma-v3.0`
- **Languages:** Kannada (`kn-IN`), English (`en-IN`)
- **Format:** `codemix` (English in Latin, Kannada in native script)
- **Limit:** 30 seconds per request

### Timbre TTS (Text-to-Speech)

- **URL:** `POST https://api.vachana.ai/api/v1/tts/inference`
- **Model:** `timbre-v3.0`
- **Voices:**
  - Kannada: `Chetana` (warm, empathetic)
  - Hindi: `Kalpana` (empathetic, composed)
  - English: `Shivani` (warm, patient)
- **Output:** WAV audio (48kHz, mono, PCM16)

---

## Security Notes

✅ **API key is backend-only** (never exposed to frontend)  
✅ **Logs never print the key** (redacted in error messages)  
✅ **`.env` is git-ignored** (won't be committed accidentally)  
✅ **Frontend requests audio via backend proxy** (key stays secure)

---

## Next Steps

After successful API validation:

1. ✅ Run full test suite: `pytest backend/tests/ -v`
2. ✅ Start development server: `uvicorn backend.app.main:app --reload`
3. ✅ Start frontend: `cd frontend && npm run dev`
4. ✅ Test emergency detection with real transcripts
5. ✅ Test TTS playback in operator dashboard

---

## Support

If you encounter issues:

1. Check this guide's **Troubleshooting** section
2. Review Gnani official docs: https://docs.gnani.ai/
3. Verify API key scopes in Gnani dashboard
4. Check application logs for detailed error messages

---

**Document Version:** 1.0  
**Last Updated:** November 8, 2026  
**Naadi Version:** 0.1.0 (Milestone 04.1 + TTS)
