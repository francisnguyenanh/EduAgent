"""Distributed Session Store backed by Firestore with in-memory fallback (Task 10.5).

Solves the multi-instance Cloud Run session state problem:
- Persists live debate sessions to Firestore collection `debate_sessions/{session_id}`
- Firestore is the SOURCE OF TRUTH; the in-memory tier is a short-lived read cache
- Supports Firestore TTL deletion via the `expire_at` timestamp
- Falls back to the local tier if Firestore is unavailable

Wave 12 Group 4 -- the bug this file used to have, and why the fix looks like this
--------------------------------------------------------------------------------
`load_session()` previously returned any cached entry whose *session* TTL (24h)
had not passed, before ever consulting Firestore, with no versioning or
invalidation. In a multi-instance deployment that loses debate turns:

    Turn 1 -> instance A     : writes {turns: [t1]}, caches {turns: [t1]}
    Turn 2 -> instance B     : loads from Firestore, writes {turns: [t1, t2]}
    Turn 3 -> instance A     : cache entry is still ~minutes old and thus "valid",
                               so it HITS the stale {turns: [t1]} -- t2 vanishes,
                               and the subsequent save_session() writes that
                               stale state back over Firestore.

So ADR-015 had narrowed the failure window without closing it: the store was
durable, but reads did not prefer the durable copy. The fix is to make the cache
honest about what it is -- a coalescing cache for near-simultaneous reads, not a
session store. Entries are trusted for `_CACHE_FRESHNESS_SECONDS` (3s) only;
past that, every read goes to Firestore.

Why 3 seconds rather than a version counter: a debate turn is gated on a human
typing a reply, so consecutive turns are seconds-to-minutes apart and always
re-read Firestore. The only reads that land inside a 3s window are the ones in a
single request's own call chain (`get_debate_session()` is called more than once
per request), which is exactly what the cache should absorb. A `version` field
would also work but adds a compare-and-set protocol to every write for a race
that a 3s bound already removes.

Remaining known limitation (stated rather than hidden): two requests for the SAME
session arriving at two instances inside the same ~3s window can still interleave
their read-modify-write. That needs a Firestore transaction or an optimistic
version check on `save_session()`. It is not reachable through the UI, which
cannot submit the next turn before the current one responds.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

_logger = logging.getLogger(__name__)

_DEFAULT_SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours -- matches the Firestore TTL policy

# How long a locally cached copy may be served without re-reading Firestore.
# This is deliberately far shorter than the session TTL: see the module docstring.
_CACHE_FRESHNESS_SECONDS = 3.0

# In-memory local cache:
#   {session_id: {"data": dict, "cached_at": float, "expires_at": float}}
# `cached_at` bounds cache freshness; `expires_at` bounds session lifetime.
_LOCAL_SESSION_CACHE: dict[str, dict] = {}


def _is_testing() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _clean_expired_local_sessions() -> None:
    now = time.time()
    expired_keys = [sid for sid, item in _LOCAL_SESSION_CACHE.items() if item.get("expires_at", 0) < now]
    for sid in expired_keys:
        _LOCAL_SESSION_CACHE.pop(sid, None)


def _cache_put(session_id: str, data: dict, ttl_seconds: int = _DEFAULT_SESSION_TTL_SECONDS) -> None:
    now = time.time()
    _LOCAL_SESSION_CACHE[session_id] = {
        "data": data,
        "cached_at": now,
        "expires_at": now + ttl_seconds,
    }


def save_session(session_id: str, data: dict, ttl_seconds: int = _DEFAULT_SESSION_TTL_SECONDS, *, client=None) -> None:
    """Saves session state to Firestore and refreshes the local cache.

    `client` is injectable so tests can assert the write really happens with the
    right payload (Wave 12 Group 4: previously the only way to keep tests off real
    Firestore was the PYTEST_CURRENT_TEST early-return below, which meant no test
    covered this code path at all).
    """
    now_dt = datetime.now(timezone.utc)
    expire_dt = now_dt + timedelta(seconds=ttl_seconds)

    _clean_expired_local_sessions()
    _cache_put(session_id, data, ttl_seconds)

    db = client or _default_client()
    if db is None:
        return

    try:
        payload = dict(data)
        payload["_session_id"] = session_id
        payload["_updated_at"] = now_dt.isoformat()
        payload["expire_at"] = expire_dt  # consumed by the Firestore TTL policy (README section 3.4, step 2)

        db.collection("debate_sessions").document(session_id).set(payload)
    except Exception as exc:
        # Non-fatal: the local tier still holds the session, so the current
        # request succeeds. It degrades to single-instance behaviour, which is
        # strictly better than failing the student's debate outright.
        _logger.warning(f"Could not persist session {session_id} to Firestore: {exc}")


def load_session(session_id: str, *, client=None) -> dict | None:
    """Loads a session, preferring Firestore as the source of truth.

    The local cache is consulted only if the entry is younger than
    `_CACHE_FRESHNESS_SECONDS`. If Firestore is unreachable, a stale cached copy
    is returned as a last resort -- losing a debate to an infrastructure blip is
    worse than serving state that is a few minutes old on one instance.
    """
    cached = _LOCAL_SESSION_CACHE.get(session_id)
    now = time.time()
    cache_is_live = bool(cached) and cached.get("expires_at", 0) > now
    if cache_is_live and (now - cached.get("cached_at", 0)) < _CACHE_FRESHNESS_SECONDS:
        return cached.get("data")

    db = client or _default_client()
    if db is None:
        return cached.get("data") if cache_is_live else None

    try:
        doc = db.collection("debate_sessions").document(session_id).get()
        if doc.exists:
            data = doc.to_dict() or {}
            for meta_field in ("_session_id", "_updated_at", "expire_at"):
                data.pop(meta_field, None)
            _cache_put(session_id, data)
            return data
        # Authoritatively absent (e.g. end_debate_session deleted it): drop any
        # local copy so this instance stops resurrecting a finished session.
        _LOCAL_SESSION_CACHE.pop(session_id, None)
        return None
    except Exception as exc:
        _logger.warning(f"Could not load session {session_id} from Firestore: {exc}")
        return cached.get("data") if cache_is_live else None


_META_FIELDS = ("_session_id", "_updated_at", "expire_at")


def claim_reflection_atomically(session_id: str, *, client=None) -> tuple[str, dict | None]:
    """Compare-and-set the `has_reflected` flag inside a Firestore transaction.

    Wave 16 #4: `interactive.claim_reflection()` used to read the session, check
    the flag, then write it back -- three separate operations. ADR-022 and the
    README claimed that "prevents double-click race condition exploits", but two
    POSTs landing on two Cloud Run instances (maxScale is 5) both read
    `has_reflected=False` and both proceeded, banking two growth bonuses. That
    is the same class of bug as ADR-015: adding a durable store does not make a
    read-modify-write atomic. The module docstring above already recorded this
    limitation for debate *turns*, where it is unreachable because the UI cannot
    send turn N+1 before turn N answers -- but a scripted double-POST to
    `/reflect` is exactly the adversarial case that exemption does not cover.

    Returns `(status, session_data)` where status is one of:
      "claimed"      -- the flag went False -> True in this transaction; caller owns it
      "already"      -- another request had already claimed it
      "not_complete" -- the debate behind this session has not finished
      "missing"      -- no such session document
      "unavailable"  -- no Firestore client (local dev / pytest); caller falls back

    The `completed` and `has_reflected` checks both happen INSIDE the
    transaction, so the decision and the write cannot be separated by another
    request.
    """
    db = client or _default_client()
    if db is None:
        return ("unavailable", None)

    try:
        from google.cloud import firestore

        doc_ref = db.collection("debate_sessions").document(session_id)

        @firestore.transactional
        def _txn(transaction) -> tuple[str, dict | None]:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return ("missing", None)
            data = snapshot.to_dict() or {}
            for meta_field in _META_FIELDS:
                data.pop(meta_field, None)
            if not data.get("completed"):
                return ("not_complete", data)
            if data.get("has_reflected"):
                return ("already", data)
            transaction.update(doc_ref, {"has_reflected": True})
            data["has_reflected"] = True
            return ("claimed", data)

        status, data = _txn(db.transaction())
        if data is not None:
            _cache_put(session_id, data)
        elif status == "missing":
            _LOCAL_SESSION_CACHE.pop(session_id, None)
        return (status, data)
    except Exception as exc:
        # Same discipline as save_session(): an infrastructure blip degrades to
        # the non-transactional path rather than failing the student outright.
        _logger.warning(f"Transactional reflection claim failed for {session_id}: {exc}")
        return ("unavailable", None)


def delete_session(session_id: str, *, client=None) -> None:
    """Deletes session from local cache and Firestore."""
    _LOCAL_SESSION_CACHE.pop(session_id, None)

    db = client or _default_client()
    if db is None:
        return

    try:
        db.collection("debate_sessions").document(session_id).delete()
    except Exception as exc:
        _logger.warning(f"Could not delete session {session_id} from Firestore: {exc}")


def store_is_authoritative(*, client=None) -> bool:
    """True when a real Firestore client backs this store.

    Wave 17 #2: `load_session()` returns None both for "this session genuinely
    does not exist" and for "there is no durable store configured at all"
    (local dev, pytest). A caller that treats those the same either resurrects
    a session another instance already deleted, or refuses to serve one that
    only exists in memory. This lets the caller tell them apart.
    """
    return (client or _default_client()) is not None


def _default_client():
    """The real Firestore client, or None when no client should be used.

    Returns None under pytest so a test that does not inject a fake client stays
    offline. Tests that DO care about the Firestore path inject one explicitly
    (see tests/test_firestore_session.py) -- that is the Wave 12 Group 4 fix for
    "the durable path had no test coverage because it was switched off by an
    environment variable".
    """
    if _is_testing():
        return None
    try:
        from eduagent.memory.firestore_memory import _client

        return _client()
    except Exception as exc:
        _logger.warning(f"Firestore client unavailable: {exc}")
        return None
