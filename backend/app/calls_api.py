"""REST endpoints for the saved-call log (SQLite)."""

from __future__ import annotations

import csv
import io
from functools import lru_cache
from typing import Any, Literal

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.services.call_store import CallNotFoundError, CallStore, summarise

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])

Label = Literal["arrest", "not_arrest"]
Noise = Literal["quiet", "kitchen", "street", "market", "other"]


class SavedUtterance(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language: str | None = Field(default=None, max_length=16)
    utterance_index: int = Field(default=0, ge=0)
    timestamp: float | None = Field(default=None, ge=0)


class SavedIndicator(BaseModel):
    phrase: str = Field(..., max_length=200)
    category: str = Field(..., max_length=40)
    utterance_index: int = Field(default=0, ge=0)
    utterance_text: str = Field(default="", max_length=2000)


class CallCreate(BaseModel):
    source: Literal["upload", "live"]
    recording_name: str | None = Field(default=None, max_length=255)
    language_code: str | None = Field(default=None, max_length=16)
    model: str | None = Field(default=None, max_length=40)
    request_id: str | None = Field(default=None, max_length=100)
    transcript: str = Field(..., min_length=1, max_length=20000)
    utterances: list[SavedUtterance] = Field(default_factory=list, max_length=500)
    analysis_status: Literal["no_indicator", "review_required", "potential_emergency"] | None = None
    risk_category: str | None = Field(default=None, max_length=40)
    matched_indicators: list[SavedIndicator] = Field(default_factory=list, max_length=200)
    transcription_ms: float | None = Field(default=None, ge=0)
    analysis_ms: float | None = Field(default=None, ge=0)
    time_to_flag_ms: float | None = Field(default=None, ge=0)
    reviewed_at: str | None = Field(default=None, max_length=40)
    label: Label | None = None
    noise_condition: Noise | None = None


class CallUpdate(BaseModel):
    label: Label | None = None
    noise_condition: Noise | None = None


@lru_cache(maxsize=1)
def _default_store() -> CallStore:
    return CallStore(get_settings().naadi_db_path)


def get_call_store() -> CallStore:
    """Dependency so tests can swap in a temporary database."""
    return _default_store()


def _not_found() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"success": False, "error": {"code": "CALL_NOT_FOUND", "message": "That saved call does not exist."}},
    )


@router.get("")
def list_calls(store: CallStore = Depends(get_call_store)) -> dict[str, Any]:
    """All saved calls, newest first, with detector performance on labelled calls."""
    calls = store.list()
    return {"calls": calls, "summary": summarise(calls)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_call(payload: CallCreate, store: CallStore = Depends(get_call_store)) -> dict[str, Any]:
    """Save one staged call. Only called when the operator presses Save."""
    return store.create(payload.model_dump())


@router.patch("/{call_id}", response_model=None)
def update_call(call_id: str, payload: CallUpdate, store: CallStore = Depends(get_call_store)) -> dict[str, Any] | JSONResponse:
    """Set or clear the ground-truth label and noise condition."""
    try:
        return store.update(call_id, payload.model_dump(exclude_unset=True))
    except CallNotFoundError:
        return _not_found()


@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_call(call_id: str, store: CallStore = Depends(get_call_store)) -> Response | JSONResponse:
    try:
        store.delete(call_id)
    except CallNotFoundError:
        return _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_calls(store: CallStore = Depends(get_call_store)) -> Response:
    store.delete_all()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/export.csv")
def export_calls(store: CallStore = Depends(get_call_store)) -> Response:
    """Saved calls as CSV, matching the evaluation sheet columns."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "created_at", "source", "recording_name", "label", "noise_condition", "language_code",
        "analysis_status", "indicators", "transcription_ms", "analysis_ms", "time_to_flag_ms",
        "reviewed_at", "transcript",
    ])
    for call in store.list(limit=10000):
        indicators = "; ".join(f"{i.get('category')}: {i.get('phrase')}" for i in call["matched_indicators"])
        writer.writerow([
            call["id"], call["created_at"], call["source"], call["recording_name"], call["label"],
            call["noise_condition"], call["language_code"], call["analysis_status"], indicators,
            call["transcription_ms"], call["analysis_ms"], call["time_to_flag_ms"], call["reviewed_at"],
            call["transcript"],
        ])
    # UTF-8 with BOM so Excel shows Kannada and Hindi correctly.
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="naadi-calls.csv"'},
    )
