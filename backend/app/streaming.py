"""WebSocket relay from the browser microphone to Gnani Prisma realtime STT.

The browser sends 1,024-byte frames of 16-bit mono PCM at real-time cadence.
This relay adds the API key and session settings on the server side, forwards
the frames to Gnani, and passes back only the fields the console needs. The
key never reaches the browser and no audio is stored.

Client -> server text frames: {"type": "stop"} ends the call after the open
utterance is committed.
Server -> client text frames: ready, speech_start, processing, transcript,
error, ended.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from urllib.parse import urlparse

from backend.app.limits import DAILY_LIMIT_MESSAGES, quota
from backend.app.config import MISSING_KEY_MESSAGE, get_settings

logger = logging.getLogger("naadi.stream")
router = APIRouter()

FRAME_BYTES = 1024
ALLOWED_SAMPLE_RATES = {8000, 16000, 44100, 48000}
STOP_GRACE_SECONDS = 4.0

_active_sessions = 0
_sessions_lock = asyncio.Lock()

_UPSTREAM_ERRORS = {
    401: ("GNANI_UNAUTHORIZED", "Gnani rejected the API key. Check GNANI_API_KEY in .env."),
    402: ("GNANI_INSUFFICIENT_CREDIT", "The Gnani account has run out of credits."),
    403: ("GNANI_SCOPE_NOT_ALLOWED", "This API key is not allowed to use realtime speech-to-text."),
    429: ("GNANI_RATE_LIMITED", "Gnani is limiting requests right now. Wait a moment and try again."),
}


def stream_language() -> str:
    """The single locale used for live calls."""
    settings = get_settings()
    if settings.gnani_stream_language_code:
        return settings.gnani_stream_language_code.strip()
    return settings.gnani_language_code.split(",")[0].strip() or "kn-IN"


def _upstream_headers(sample_rate: int) -> dict[str, str]:
    settings = get_settings()
    return {
        "x-api-key-id": settings.gnani_api_key or "",
        # The docs list both spellings; the realtime server currently selects
        # Prisma v3.0 only from x-model, so send both to be safe.
        "model": settings.gnani_model,
        "x-model": settings.gnani_model,
        # Realtime accepts exactly one locale (verified 9 Nov 2026), unlike REST.
        "language_code": stream_language(),
        "format": settings.gnani_format,
        "x-format": settings.gnani_format,
        "x-sample-rate": str(sample_rate),
        # Callers go quiet while doing compressions, so allow long silences.
        "x-idle-timeout-sec": "180",
        # Speakerphone audio: ignore short clicks and horns, close a sentence
        # after 600 ms of silence, and force a transcript on long monologues.
        "x-vad-threshold": "0.65",
        "x-min-speech-ms": "200",
        "x-min-silence-ms": "600",
        "x-max-speech-s": "12",
    }


def _client_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Keep only the upstream fields the console uses."""

    kind = message.get("type")
    if kind == "transcript":
        text = (message.get("text") or "").strip()
        if not text:
            return None
        return {
            "type": "transcript",
            "text": text,
            "detected_language_code": message.get("detected_language_code"),
            "segment_index": message.get("segment_index"),
            "latency_ms": message.get("latency"),
            "audio_duration_ms": message.get("audio_duration_ms"),
        }
    if kind in ("speech_start", "processing"):
        return {"type": kind}
    if kind == "error":
        return {"type": "error", "code": "GNANI_STREAM_ERROR", "message": str(message.get("message") or "Gnani reported an error.")[:300]}
    return None


async def _send(websocket: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))
    except (RuntimeError, WebSocketDisconnect):
        pass


async def _fail(websocket: WebSocket, code: str, message: str, close_code: int = 1011) -> None:
    await _send(websocket, {"type": "error", "code": code, "message": message})
    try:
        await websocket.close(code=close_code)
    except RuntimeError:
        pass


@router.websocket("/api/v1/stream")
async def stream(websocket: WebSocket) -> None:
    global _active_sessions
    settings = get_settings()

    # Browsers do not apply CORS to WebSockets, so check the origin here. The
    # deployed site connects from its own host, which is always allowed.
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origins and urlparse(origin).netloc != websocket.headers.get("host"):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    if not settings.has_gnani_api_key:
        await _fail(websocket, "GNANI_NOT_CONFIGURED", MISSING_KEY_MESSAGE)
        return

    remaining = quota.remaining("live_seconds")
    if remaining < 5:
        await _fail(websocket, "DAILY_LIMIT_REACHED", DAILY_LIMIT_MESSAGES["live_seconds"], 1013)
        return
    session_limit = int(min(settings.stream_max_seconds, remaining))

    try:
        sample_rate = int(websocket.query_params.get("sample_rate", "16000"))
    except ValueError:
        sample_rate = 0
    if sample_rate not in ALLOWED_SAMPLE_RATES:
        await _fail(websocket, "INVALID_SAMPLE_RATE", "Sample rate must be 8000, 16000, 44100 or 48000 Hz.", 1008)
        return

    async with _sessions_lock:
        if _active_sessions >= settings.stream_max_sessions:
            busy = True
        else:
            busy = False
            _active_sessions += 1
    if busy:
        await _fail(websocket, "STREAM_BUSY", "Another live call is already running. Stop it before starting a new one.", 1013)
        return

    started = time.monotonic()
    try:
        try:
            upstream = await websockets.connect(
                settings.gnani_stream_url,
                additional_headers=_upstream_headers(sample_rate),
                open_timeout=10,
                close_timeout=2,
                max_size=2**20,
            )
        except InvalidStatus as exc:
            status_code = exc.response.status_code
            code, message = _UPSTREAM_ERRORS.get(
                status_code, ("GNANI_STREAM_REJECTED", f"Gnani refused the realtime connection (HTTP {status_code}).")
            )
            logger.warning("Gnani realtime handshake refused: status=%s", status_code)
            await _fail(websocket, code, message)
            return
        except (OSError, TimeoutError) as exc:
            logger.warning("Gnani realtime connection failed: %s", type(exc).__name__)
            await _fail(websocket, "GNANI_STREAM_UNREACHABLE", "Could not reach Gnani's realtime service. Check the internet connection.")
            return

        state = {"speaking": False, "stopping": False}
        settled = asyncio.Event()

        async def browser_to_gnani() -> str:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return "disconnected"
                data = message.get("bytes")
                if data is not None:
                    if len(data) != FRAME_BYTES:
                        continue  # Gnani requires exact 1,024-byte frames
                    await upstream.send(data)
                    continue
                text = message.get("text")
                if text:
                    try:
                        control = json.loads(text)
                    except ValueError:
                        continue
                    if control.get("type") == "stop":
                        state["stopping"] = True
                        if not state["speaking"]:
                            settled.set()
                        await upstream.send(json.dumps({"type": "commit"}))
                        return "stopped"

        async def gnani_to_browser() -> str:
            async for raw in upstream:
                if isinstance(raw, bytes):
                    continue
                try:
                    message = json.loads(raw)
                except ValueError:
                    continue
                kind = message.get("type")
                if kind == "connected":
                    await _send(websocket, {
                        "type": "ready",
                        "sample_rate": sample_rate,
                        "model": settings.gnani_model,
                        "language_code": stream_language(),
                        "max_seconds": settings.stream_max_seconds,
                    })
                    continue
                if kind == "speech_start":
                    state["speaking"] = True
                elif kind == "transcript":
                    state["speaking"] = False
                    if state["stopping"]:
                        settled.set()
                forwarded = _client_message(message)
                if forwarded is not None:
                    await _send(websocket, forwarded)
            return "upstream_closed"

        to_gnani = asyncio.create_task(browser_to_gnani())
        to_browser = asyncio.create_task(gnani_to_browser())
        try:
            done, _ = await asyncio.wait(
                {to_gnani, to_browser},
                timeout=session_limit,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                if session_limit < settings.stream_max_seconds:
                    message = DAILY_LIMIT_MESSAGES["live_seconds"]
                else:
                    message = f"Live calls stop after {settings.stream_max_seconds // 60} minutes."
                await _send(websocket, {"type": "error", "code": "STREAM_TIME_LIMIT", "message": message})
            elif to_gnani in done and not to_gnani.cancelled() and to_gnani.exception() is None and to_gnani.result() == "stopped":
                # Give Gnani a moment to return the sentence that was still open.
                try:
                    await asyncio.wait_for(settled.wait(), timeout=STOP_GRACE_SECONDS)
                except TimeoutError:
                    pass
            elif to_browser in done and to_browser.exception() is not None:
                exc = to_browser.exception()
                if isinstance(exc, ConnectionClosed):
                    await _send(websocket, {"type": "error", "code": "GNANI_STREAM_CLOSED", "message": "Gnani closed the live session."})
        finally:
            for task in (to_gnani, to_browser):
                task.cancel()
            await asyncio.gather(to_gnani, to_browser, return_exceptions=True)
            await upstream.close()
            quota.add("live_seconds", time.monotonic() - started)

        await _send(websocket, {"type": "ended", "seconds": round(time.monotonic() - started, 1)})
        try:
            await websocket.close()
        except RuntimeError:
            pass
    finally:
        async with _sessions_lock:
            _active_sessions -= 1
        logger.info("Live session ended after %.1fs", time.monotonic() - started)
