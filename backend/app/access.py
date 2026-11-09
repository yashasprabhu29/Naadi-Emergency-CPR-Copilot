"""Access code and daily usage caps, so a public deployment cannot drain Gnani credits.

When NAADI_ACCESS_CODE is set, every /api/v1/* endpoint except health and
access verification needs the header ``X-Naadi-Access: <code>``. The live
WebSocket checks the code in its first message instead, because browsers
cannot set headers on WebSockets. Daily caps apply whether or not a code is set.
"""

from __future__ import annotations

import hmac
import threading
import time
from datetime import date

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import get_settings

ACCESS_HEADER = "X-Naadi-Access"
PUBLIC_PATHS = {"/api/v1/health", "/api/v1/access/verify"}

router = APIRouter(prefix="/api/v1/access", tags=["access"])


def access_required() -> bool:
    return bool((get_settings().naadi_access_code or "").strip())


def code_matches(candidate: str | None) -> bool:
    expected = (get_settings().naadi_access_code or "").strip()
    if not expected:
        return True
    return hmac.compare_digest((candidate or "").strip().encode(), expected.encode())


def client_ip(request_or_ws) -> str:
    client = getattr(request_or_ws, "client", None)
    return client.host if client else "unknown"


class _FailedAttempts:
    """Slows down guessing: at most 10 wrong codes per IP per 10 minutes."""

    WINDOW_SECONDS = 600
    LIMIT = 10

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def blocked(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._hits.get(ip, []) if now - t < self.WINDOW_SECONDS]
            self._hits[ip] = hits
            return len(hits) >= self.LIMIT

    def record(self, ip: str) -> None:
        with self._lock:
            self._hits.setdefault(ip, []).append(time.monotonic())


failed_attempts = _FailedAttempts()


class DailyQuota:
    """In-memory per-day counters. They reset at midnight (server time) and on restart."""

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


def _deny(code: str, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": code, "message": message}})


class AccessCodeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            access_required()
            and request.method != "OPTIONS"
            and path.startswith("/api/v1/")
            and path not in PUBLIC_PATHS
            and request.scope.get("type") == "http"
        ):
            if not code_matches(request.headers.get(ACCESS_HEADER)):
                return _deny("ACCESS_CODE_REQUIRED", "Enter the access code to use Naadi.")
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "microphone=(self), camera=(), geolocation=()")
        return response


class AccessCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=200)


@router.post("/verify", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def verify_access_code(payload: AccessCodeRequest, request: Request) -> JSONResponse | None:
    """Check an access code. Wrong guesses are rate limited per IP."""
    ip = client_ip(request)
    if failed_attempts.blocked(ip):
        return _deny("TOO_MANY_ATTEMPTS", "Too many wrong codes. Wait 10 minutes and try again.", status.HTTP_429_TOO_MANY_REQUESTS)
    if not code_matches(payload.code):
        failed_attempts.record(ip)
        return _deny("ACCESS_CODE_INVALID", "That access code is not right.")
    return None
