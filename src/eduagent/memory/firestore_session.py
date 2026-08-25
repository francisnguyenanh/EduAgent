"""Distributed Session Store backed by Firestore with in-memory fallback (Task 10.5).

Solves the multi-instance Cloud Run session state problem:
- Persists live debate sessions to Firestore collection `debate_sessions/{session_id}`
- Supports Firestore TTL policies via `expire_at` timestamp
- Transparent local in-memory caching to minimize Firestore read latency
- Resilient fallback to memory if Firestore is unavailable
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

_logger = logging.getLogger(__name__)

_DEFAULT_SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours

# In-memory local cache: {session_id: {"data": dict, "expires_at": float}}
_LOCAL_SESSION_CACHE: dict[str, dict] = {}


def _is_testing() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _clean_expired_local_sessions() -> None:
    now = time.time()
    expired_keys = [sid for sid, item in _LOCAL_SESSION_CACHE.items() if item.get("expires_at", 0) < now]
    for sid in expired_keys:
        _LOCAL_SESSION_CACHE.pop(sid, None)


def save_session(session_id: str, data: dict, ttl_seconds: int = _DEFAULT_SESSION_TTL_SECONDS) -> None:
    """Saves session state to both local in-memory cache and Firestore."""
    now_dt = datetime.now(timezone.utc)
    expire_dt = now_dt + timedelta(seconds=ttl_seconds)

    # 1. Update local cache
    _clean_expired_local_sessions()
    _LOCAL_SESSION_CACHE[session_id] = {
        "data": data,
        "expires_at": time.time() + ttl_seconds,
    }

    # 2. Persist to Firestore if not disabled in unit tests
    if _is_testing():
        return

    try:
        from eduagent.memory.firestore_memory import _client

        payload = dict(data)
        payload["_session_id"] = session_id
        payload["_updated_at"] = now_dt.isoformat()
        payload["expire_at"] = expire_dt  # Firestore TTL field

        _client().collection("debate_sessions").document(session_id).set(payload)
    except Exception as exc:
        _logger.warning(f"Could not persist session {session_id} to Firestore: {exc}")


def load_session(session_id: str) -> dict | None:
    """Loads session from local cache or Firestore."""
    # 1. Check local cache
    cached = _LOCAL_SESSION_CACHE.get(session_id)
    if cached and cached.get("expires_at", 0) > time.time():
        return cached.get("data")

    # 2. Query Firestore
    if _is_testing():
        return None

    try:
        from eduagent.memory.firestore_memory import _client

        doc = _client().collection("debate_sessions").document(session_id).get()
        if doc.exists:
            data = doc.to_dict() or {}
            # Strip metadata fields
            data.pop("_session_id", None)
            data.pop("_updated_at", None)
            data.pop("expire_at", None)

            # Warm local cache
            _LOCAL_SESSION_CACHE[session_id] = {
                "data": data,
                "expires_at": time.time() + _DEFAULT_SESSION_TTL_SECONDS,
            }
            return data
    except Exception as exc:
        _logger.warning(f"Could not load session {session_id} from Firestore: {exc}")

    return None


def delete_session(session_id: str) -> None:
    """Deletes session from local cache and Firestore."""
    _LOCAL_SESSION_CACHE.pop(session_id, None)

    if _is_testing():
        return

    try:
        from eduagent.memory.firestore_memory import _client

        _client().collection("debate_sessions").document(session_id).delete()
    except Exception as exc:
        _logger.warning(f"Could not delete session {session_id} from Firestore: {exc}")
