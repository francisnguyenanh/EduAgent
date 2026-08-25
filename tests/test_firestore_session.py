"""Unit tests for Distributed Firestore Session Store (Task 10.5)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from eduagent.memory.firestore_session import (
    _LOCAL_SESSION_CACHE,
    _clean_expired_local_sessions,
    delete_session,
    load_session,
    save_session,
)


def test_save_and_load_local_session():
    sid = "test_sess_01"
    data = {"persona_id": "skeptic", "essay_text": "Sample text", "turns": []}
    
    save_session(sid, data, ttl_seconds=3600)
    loaded = load_session(sid)
    
    assert loaded is not None
    assert loaded["persona_id"] == "skeptic"
    assert loaded["essay_text"] == "Sample text"


def test_delete_session():
    sid = "test_sess_del"
    save_session(sid, {"persona_id": "nitpicker"})
    assert load_session(sid) is not None
    
    delete_session(sid)
    assert load_session(sid) is None


def test_local_cache_eviction_on_expiry():
    sid = "test_sess_exp"
    # Insert session that expires immediately
    _LOCAL_SESSION_CACHE[sid] = {
        "data": {"persona_id": "expander"},
        "expires_at": time.time() - 10,
    }
    
    _clean_expired_local_sessions()
    assert sid not in _LOCAL_SESSION_CACHE
    assert load_session(sid) is None
