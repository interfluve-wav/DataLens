"""Shared limits and helpers for API hardening."""

from __future__ import annotations

import logging
import os
import re
import secrets
import threading
import time
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from fastapi import HTTPException, UploadFile

logger = logging.getLogger("datalens")

MAX_UPLOAD_BYTES = int(os.environ.get("DATALENS_MAX_UPLOAD_BYTES", 500 * 1024 * 1024))
MAX_FETCH_BYTES = int(os.environ.get("DATALENS_MAX_FETCH_BYTES", 500 * 1024 * 1024))
MAX_ROWS = int(os.environ.get("DATALENS_MAX_ROWS", 1_000_000))
MAX_COLUMNS = int(os.environ.get("DATALENS_MAX_COLUMNS", 500))
MAX_SESSIONS = int(os.environ.get("DATALENS_MAX_SESSIONS", 100))
SESSION_TTL_SECONDS = int(os.environ.get("DATALENS_SESSION_TTL_SECONDS", 86_400))

VALID_FIX_TYPES = frozenset(
    {"drop_nulls", "impute_median", "impute_mode", "strip_whitespace", "dedupe"}
)

_session_lock = threading.Lock()


def new_session_id() -> str:
    return secrets.token_urlsafe(24)


def sanitize_filename(name: Optional[str]) -> str:
    if not name:
        return "upload.dat"
    base = name.replace("\\", "/").split("/")[-1].strip()
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    if not base or base in {".", ".."}:
        return "upload.dat"
    return base[:200]


async def read_upload_bounded(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
            raise HTTPException(
                413,
                f"File too large (max {max_mb} MB). Set DATALENS_MAX_UPLOAD_BYTES to raise the limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def enforce_fetch_size(content: bytes, label: str = "response") -> None:
    if len(content) > MAX_FETCH_BYTES:
        max_mb = MAX_FETCH_BYTES // (1024 * 1024)
        raise ValueError(
            f"{label} exceeds size limit ({max_mb} MB). "
            "Set DATALENS_MAX_FETCH_BYTES to raise the limit."
        )


def enforce_dataframe_limits(df: pd.DataFrame) -> None:
    if len(df.columns) > MAX_COLUMNS:
        raise ValueError(
            f"Too many columns ({len(df.columns)}). Maximum is {MAX_COLUMNS}."
        )
    if len(df) > MAX_ROWS:
        raise ValueError(
            f"Too many rows ({len(df):,}). Maximum is {MAX_ROWS:,}. "
            "Set DATALENS_MAX_ROWS to raise the limit."
        )


def validate_fixes(fixes: Dict[str, str]) -> None:
    if not fixes:
        raise ValueError("No fixes specified")
    unknown = {v for v in fixes.values() if v not in VALID_FIX_TYPES}
    if unknown:
        raise ValueError(f"Unknown fix type(s): {', '.join(sorted(unknown))}")


def store_session(
    sessions: Dict[str, Dict[str, Any]], session_id: str, session: Dict[str, Any]
) -> None:
    session["_created_at"] = time.time()
    session["_last_access"] = time.time()
    with _session_lock:
        _evict_sessions(sessions)
        sessions[session_id] = session


def touch_session(sessions: Dict[str, Dict[str, Any]], session_id: str) -> Dict[str, Any]:
    with _session_lock:
        session = sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        session["_last_access"] = time.time()
        return session


def delete_session(sessions: Dict[str, Dict[str, Any]], session_id: str) -> bool:
    with _session_lock:
        return sessions.pop(session_id, None) is not None


def _evict_sessions(sessions: Dict[str, Dict[str, Any]]) -> None:
    now = time.time()
    expired = [
        sid
        for sid, s in sessions.items()
        if now - s.get("_last_access", s.get("_created_at", now)) > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        sessions.pop(sid, None)

    if len(sessions) <= MAX_SESSIONS:
        return

    ranked = sorted(
        sessions.items(),
        key=lambda item: item[1].get("_last_access", 0),
    )
    for sid, _ in ranked[: max(0, len(sessions) - MAX_SESSIONS)]:
        sessions.pop(sid, None)


def client_error(message: str, exc: Optional[Exception] = None) -> HTTPException:
    if exc is not None:
        logger.warning("%s: %s", message, exc)
    return HTTPException(400, message)
