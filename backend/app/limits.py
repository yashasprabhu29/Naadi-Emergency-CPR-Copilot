"""Daily usage caps and security headers for the public deployment.

The site is open to everyone, so these caps are what stop a busy day (or a
misbehaving visitor) from draining the Gnani credits. Counters live in memory
and reset at midnight (server time) and whenever the server restarts.
"""

from __future__ import annotations

import threading
from datetime import date

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import get_settings


class DailyQuota:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = date.today()
        self._used: dict[str, float] = {}

    def _roll(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._used = {}

    def limit(self, kind: str) -> float:
        settings = get_settings()
        return {
            "transcriptions": settings.naadi_daily_transcriptions,
            "live_seconds": settings.naadi_daily_live_minutes * 60,
            "tts": settings.naadi_daily_tts,
        }[kind]

    def remaining(self, kind: str) -> float:
        with self._lock:
            self._roll()
            return max(0.0, self.limit(kind) - self._used.get(kind, 0.0))

    def try_consume(self, kind: str, amount: float = 1.0) -> bool:
        with self._lock:
            self._roll()
            used = self._used.get(kind, 0.0)
            if used + amount > self.limit(kind):
                return False
            self._used[kind] = used + amount
            return True

    def add(self, kind: str, amount: float) -> None:
        with self._lock:
            self._roll()
            self._used[kind] = self._used.get(kind, 0.0) + amount


quota = DailyQuota()

DAILY_LIMIT_MESSAGES = {
    "transcriptions": "Today's transcription limit for this demo has been reached. Try again tomorrow.",
    "live_seconds": "Today's live-audio limit for this demo has been reached. Try again tomorrow.",
    "tts": "Today's coaching-audio limit for this demo has been reached. Try again tomorrow.",
}


def daily_limit_response(kind: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"success": False, "error": {"code": "DAILY_LIMIT_REACHED", "message": DAILY_LIMIT_MESSAGES[kind]}},
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "microphone=(self), camera=(), geolocation=()")
        return response
