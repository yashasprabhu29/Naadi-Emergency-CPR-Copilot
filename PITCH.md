# Naadi (ನಾಡಿ): CPR coaching on noisy emergency calls, in the caller's language

**Live demo:** https://naadi-emergency.onrender.com · **Built on:** Gnani Prisma v3.0 (speech-to-text) and Gnani Timbre v3.0 (text-to-speech)

## Problem

When a heart stops outside hospital, survival depends on someone starting CPR within minutes. In India few bystanders do: in one South Indian hospital study only 7.4% of out-of-hospital cardiac arrest patients had received bystander CPR. A 108 call-taker can coach CPR over the phone, but callers are panicking, on speakerphone, in traffic, and often mixing Kannada and English. The American Heart Association's telephone-CPR quality measures exclude language-barrier calls as unidentifiable. Naadi is built for those calls.

## Solution

Naadi is a copilot for emergency call-takers. It listens to the call, transcribes the caller live, flags a possible cardiac arrest when the caller describes someone who is unresponsive and not breathing normally, and, once the call-taker confirms, coaches hands-only CPR in the caller's own language with a 110-per-minute beat.

## How it works

1. **Listen.** A recorded call (up to 30 s) goes to Prisma v3.0 over REST. A live call streams from the browser microphone as 1,024-byte PCM frames over a WebSocket to the Naadi backend, which relays it to Prisma's realtime API. The API key stays on the server and no audio is stored.
2. **Detect.** After every sentence, a rule-based detector checks the caller's last three sentences in Kannada, Hindi and English for two signs together: unresponsive and abnormal breathing. Negations ("he is breathing") downgrade the result to review required. Every flag shows the exact words behind it. No LLM is in the loop.
3. **Confirm.** A human call-taker reviews every flag before anything happens.
4. **Coach.** Fixed, pre-written CPR instructions are voiced by Timbre in Kannada, Hindi or English, followed by a metronome at 110 compressions per minute with a count, a timer and a reminder to swap rescuers every two minutes.
5. **Measure.** Each staged call can be saved with a ground-truth label and noise condition. The Call log reports arrests flagged, false flags and median time to flag (AHA target: under 90 seconds), with CSV export.

## Why Gnani

Prisma is trained on 14M+ hours of telephonic audio and handles code-mixed speech and per-sentence language detection, which is exactly what a noisy 108 call needs. Timbre speaks every supported Indian language, so the coaching voice can match the caller.

## Stack and safety

React + Vite console, FastAPI backend, SQLite call log, one Docker service on Render. Human confirmation on every flag, fixed coaching text, no audio retention, calls saved only on request, and daily usage caps to protect credits.

**Status:** prototype for Gnani AI's Great Indian AI Internship Challenge. Not a medical device and not connected to 108/112. In an emergency, call 108 or 112.
