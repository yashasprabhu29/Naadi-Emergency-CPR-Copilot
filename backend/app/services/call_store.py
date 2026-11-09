"""SQLite storage for staged calls the operator chooses to save.

Nothing is written unless the operator presses Save in the console. Records
hold the transcript, the detection result and timings, so a team can label
each staged call (arrest or not) and measure the detector over a test set.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LABELS = ("arrest", "not_arrest")
NOISE_CONDITIONS = ("quiet", "kitchen", "street", "market", "other")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('upload', 'live')),
    recording_name TEXT,
    language_code TEXT,
    model TEXT,
    request_id TEXT,
    transcript TEXT NOT NULL,
    utterances_json TEXT NOT NULL DEFAULT '[]',
    analysis_status TEXT,
    risk_category TEXT,
    indicators_json TEXT NOT NULL DEFAULT '[]',
    transcription_ms REAL,
    analysis_ms REAL,
    time_to_flag_ms REAL,
    reviewed_at TEXT,
    label TEXT CHECK (label IS NULL OR label IN ('arrest', 'not_arrest')),
    noise_condition TEXT CHECK (
        noise_condition IS NULL OR noise_condition IN ('quiet', 'kitchen', 'street', 'market', 'other')
    )
);
CREATE INDEX IF NOT EXISTS calls_created_at ON calls (created_at DESC);
"""

_COLUMNS = (
    "id", "created_at", "source", "recording_name", "language_code", "model", "request_id",
    "transcript", "utterances_json", "analysis_status", "risk_category", "indicators_json",
    "transcription_ms", "analysis_ms", "time_to_flag_ms", "reviewed_at", "label", "noise_condition",
)


class CallNotFoundError(LookupError):
    """Raised when a call id does not exist."""


class CallStore:
    """Small, thread-safe wrapper around one SQLite file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        if not self._ready:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        if not self._ready:
            connection.executescript(_SCHEMA)
            self._ready = True
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """One locked connection: commits on success, rolls back on error, always closes."""
        with self._lock:
            connection = self._connect()
            try:
                with connection:
                    yield connection
            finally:
                connection.close()

    @staticmethod
    def _to_dict(row: sqlite3.Row) -> dict[str, Any]:
        record = dict(row)
        record["utterances"] = json.loads(record.pop("utterances_json") or "[]")
        record["matched_indicators"] = json.loads(record.pop("indicators_json") or "[]")
        return record

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": data["source"],
            "recording_name": data.get("recording_name"),
            "language_code": data.get("language_code"),
            "model": data.get("model"),
            "request_id": data.get("request_id"),
            "transcript": data["transcript"],
            "utterances_json": json.dumps(data.get("utterances") or [], ensure_ascii=False),
            "analysis_status": data.get("analysis_status"),
            "risk_category": data.get("risk_category"),
            "indicators_json": json.dumps(data.get("matched_indicators") or [], ensure_ascii=False),
            "transcription_ms": data.get("transcription_ms"),
            "analysis_ms": data.get("analysis_ms"),
            "time_to_flag_ms": data.get("time_to_flag_ms"),
            "reviewed_at": data.get("reviewed_at"),
            "label": data.get("label"),
            "noise_condition": data.get("noise_condition"),
        }
        placeholders = ", ".join("?" for _ in _COLUMNS)
        with self._session() as connection:
            connection.execute(
                f"INSERT INTO calls ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
                [record[column] for column in _COLUMNS],
            )
        return self.get(record["id"])

    def get(self, call_id: str) -> dict[str, Any]:
        with self._session() as connection:
            row = connection.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        if row is None:
            raise CallNotFoundError(call_id)
        return self._to_dict(row)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM calls ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._to_dict(row) for row in rows]

    def update(self, call_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        allowed = {key: value for key, value in changes.items() if key in ("label", "noise_condition")}
        if allowed:
            assignments = ", ".join(f"{key} = ?" for key in allowed)
            with self._session() as connection:
                cursor = connection.execute(
                    f"UPDATE calls SET {assignments} WHERE id = ?", [*allowed.values(), call_id]
                )
                if cursor.rowcount == 0:
                    raise CallNotFoundError(call_id)
        return self.get(call_id)

    def delete(self, call_id: str) -> None:
        with self._session() as connection:
            cursor = connection.execute("DELETE FROM calls WHERE id = ?", (call_id,))
        if cursor.rowcount == 0:
            raise CallNotFoundError(call_id)

    def delete_all(self) -> int:
        with self._session() as connection:
            cursor = connection.execute("DELETE FROM calls")
        return cursor.rowcount


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def summarise(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Detector performance on the calls the team has labelled."""

    arrest = [call for call in calls if call.get("label") == "arrest"]
    not_arrest = [call for call in calls if call.get("label") == "not_arrest"]

    def flagged(items: list[dict[str, Any]], status: str = "potential_emergency") -> int:
        return sum(1 for call in items if call.get("analysis_status") == status)

    by_noise: dict[str, dict[str, int]] = {}
    for call in arrest + not_arrest:
        bucket = by_noise.setdefault(
            call.get("noise_condition") or "unset",
            {"arrest": 0, "arrest_flagged": 0, "not_arrest": 0, "false_flags": 0},
        )
        is_flag = call.get("analysis_status") == "potential_emergency"
        if call["label"] == "arrest":
            bucket["arrest"] += 1
            bucket["arrest_flagged"] += int(is_flag)
        else:
            bucket["not_arrest"] += 1
            bucket["false_flags"] += int(is_flag)

    return {
        "total": len(calls),
        "labelled": len(arrest) + len(not_arrest),
        "arrest_calls": len(arrest),
        "arrest_flagged": flagged(arrest),
        "arrest_review_required": flagged(arrest, "review_required"),
        "not_arrest_calls": len(not_arrest),
        "false_flags": flagged(not_arrest),
        "median_time_to_flag_ms": _median(
            [call["time_to_flag_ms"] for call in calls if call.get("time_to_flag_ms") is not None]
        ),
        "median_transcription_ms": _median(
            [call["transcription_ms"] for call in calls if call.get("transcription_ms") is not None]
        ),
        "by_noise_condition": by_noise,
    }
