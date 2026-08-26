"""Unit tests for the Distributed Firestore Session Store (Task 10.5).

ĐỢT 12 NHÓM 4: the previous version of this file imported `MagicMock, patch`
without using them, and its three tests all went through the same in-process
`_LOCAL_SESSION_CACHE` -- so nothing exercised the Firestore path at all, and
Task 10.5's stated DoD ("unit test simulating 2 consecutive requests hitting 2
independent processes") had no test behind it. The tests below use an injected
fake Firestore client, which is what makes both the multi-instance scenario and
the actual persistence payload assertable.
"""

from __future__ import annotations

import copy
import threading
import time

import pytest

from eduagent.memory import firestore_session
from eduagent.memory.firestore_session import (
    _CACHE_FRESHNESS_SECONDS,
    _LOCAL_SESSION_CACHE,
    _clean_expired_local_sessions,
    delete_session,
    load_session,
    save_session,
)


class FakeDoc:
    """DEEP-copies on both read and write, because real Firestore serializes.

    This detail matters more than it looks: with a shallow `dict(...)` copy, the
    nested `turns` list stays aliased across every "instance" in these tests, so
    an append made by instance B silently appears in instance A's cached copy --
    and the multi-instance regression test below then passes even with the bug
    reintroduced. A fake that is more forgiving than production turns a real
    regression test into decoration. Verified by re-running that test against
    the old cache-first read: it fails, as it should.
    """

    def __init__(self, store: dict, doc_id: str):
        self._store = store
        self._id = doc_id

    # -- read side --
    @property
    def exists(self) -> bool:
        return self._id in self._store

    def to_dict(self) -> dict | None:
        value = self._store.get(self._id)
        return copy.deepcopy(value) if value is not None else None

    def get(self) -> "FakeDoc":
        return self

    # -- write side --
    def set(self, payload: dict) -> None:
        self._store[self._id] = copy.deepcopy(payload)

    def delete(self) -> None:
        self._store.pop(self._id, None)


class FakeCollection:
    def __init__(self, store: dict):
        self._store = store

    def document(self, doc_id: str) -> FakeDoc:
        return FakeDoc(self._store, doc_id)


class FakeFirestore:
    """Stands in for the real Firestore client. Shared between two 'instances'
    to model the one thing that is genuinely shared in Cloud Run: the database."""

    def __init__(self):
        self.store: dict[str, dict] = {}

    def collection(self, name: str) -> FakeCollection:
        assert name == "debate_sessions"
        return FakeCollection(self.store)


@pytest.fixture
def db():
    return FakeFirestore()


@pytest.fixture(autouse=True)
def _clear_cache():
    _LOCAL_SESSION_CACHE.clear()
    yield
    _LOCAL_SESSION_CACHE.clear()


# ------------------------------------------------------------- basic round-trip


def test_save_and_load_session(db):
    data = {"persona_id": "skeptic", "essay_text": "Sample text", "turns": []}
    save_session("sess-01", data, ttl_seconds=3600, client=db)

    loaded = load_session("sess-01", client=db)
    assert loaded is not None
    assert loaded["persona_id"] == "skeptic"
    assert loaded["essay_text"] == "Sample text"


def test_save_writes_the_expected_firestore_payload(db):
    """The durable write itself is now asserted -- previously it was switched off
    under pytest, so no test could see whether it happened or what it wrote."""
    save_session("sess-02", {"persona_id": "nitpicker", "turns": [{"turn": 1}]}, ttl_seconds=3600, client=db)

    stored = db.store["sess-02"]
    assert stored["persona_id"] == "nitpicker"
    assert stored["turns"] == [{"turn": 1}]
    assert stored["_session_id"] == "sess-02"
    assert stored["_updated_at"]
    # Required for the Firestore TTL policy (deploy.txt STEP 2) to ever delete it.
    assert "expire_at" in stored


def test_delete_session_removes_from_both_tiers(db):
    save_session("sess-03", {"persona_id": "expander"}, client=db)
    assert load_session("sess-03", client=db) is not None

    delete_session("sess-03", client=db)
    assert "sess-03" not in db.store
    assert load_session("sess-03", client=db) is None


def test_local_cache_eviction_on_expiry(db):
    _LOCAL_SESSION_CACHE["sess-exp"] = {
        "data": {"persona_id": "expander"},
        "cached_at": time.time(),
        "expires_at": time.time() - 10,
    }
    _clean_expired_local_sessions()
    assert "sess-exp" not in _LOCAL_SESSION_CACHE
    assert load_session("sess-exp", client=db) is None


# ------------------------------------------------- the multi-instance bug (DoD)


def test_two_instances_do_not_lose_a_debate_turn(db):
    """Task 10.5's DoD, and a direct regression test for the ĐỢT 12 NHÓM 4 bug.

    Instance A handles turn 1, instance B handles turn 2, then the load balancer
    sends turn 3 back to instance A. Before the fix, A served its stale cached
    copy (`turns: [t1]`) because the entry was still within the 24h session TTL,
    so turn 2 was silently dropped and then overwritten in Firestore.

    Two independent processes are modelled by clearing the module-level cache
    (that is precisely what a different process has: no cache) while keeping the
    same fake Firestore, which is the one thing genuinely shared.
    """
    sid = "sess-multi"

    # --- instance A: turn 1 ---
    save_session(sid, {"student_id": "c1_stu01", "turns": [{"turn": 1}]}, client=db)
    instance_a_cache = dict(_LOCAL_SESSION_CACHE)

    # --- instance B: turn 2 (cold cache) ---
    _LOCAL_SESSION_CACHE.clear()
    session_b = load_session(sid, client=db)
    assert session_b is not None
    session_b["turns"].append({"turn": 2})
    save_session(sid, session_b, client=db)

    # --- instance A again: turn 3, with its ORIGINAL warm (now stale) cache ---
    _LOCAL_SESSION_CACHE.clear()
    _LOCAL_SESSION_CACHE.update(instance_a_cache)
    # Age the cached entry past the freshness bound, as real think-time would.
    for entry in _LOCAL_SESSION_CACHE.values():
        entry["cached_at"] = time.time() - (_CACHE_FRESHNESS_SECONDS + 1)

    session_a = load_session(sid, client=db)
    assert session_a is not None
    assert [t["turn"] for t in session_a["turns"]] == [1, 2], (
        "instance A served a stale cached session and lost turn 2 -- the exact "
        "multi-instance bug ADR-015 was meant to fix"
    )


def test_fresh_cache_is_still_used_within_the_freshness_window(db):
    """The cache must still absorb repeated reads inside one request, otherwise
    every `get_debate_session()` call becomes a Firestore round trip."""
    save_session("sess-fresh", {"turns": [{"turn": 1}]}, client=db)
    # Mutate Firestore behind the cache's back; a fresh cache should not see it.
    db.store["sess-fresh"]["turns"] = [{"turn": 1}, {"turn": 2}]

    loaded = load_session("sess-fresh", client=db)
    assert loaded is not None
    assert len(loaded["turns"]) == 1, "read inside the freshness window should be served from cache"


def test_firestore_absence_clears_a_stale_local_copy(db):
    """After end_debate_session() on another instance, this instance must stop
    resurrecting the finished session from its own cache."""
    save_session("sess-gone", {"turns": []}, client=db)
    db.store.pop("sess-gone")  # deleted elsewhere
    for entry in _LOCAL_SESSION_CACHE.values():
        entry["cached_at"] = time.time() - (_CACHE_FRESHNESS_SECONDS + 1)

    assert load_session("sess-gone", client=db) is None
    assert "sess-gone" not in _LOCAL_SESSION_CACHE


# ------------------------------------------------------------------ resilience


class BrokenFirestore(FakeFirestore):
    def collection(self, name: str):
        raise RuntimeError("Firestore unavailable")


def test_stale_cache_is_served_when_firestore_is_down():
    """Losing a student's debate to an infrastructure blip is worse than serving
    state that is a few seconds old on one instance."""
    healthy = FakeFirestore()
    save_session("sess-resil", {"turns": [{"turn": 1}]}, client=healthy)
    for entry in _LOCAL_SESSION_CACHE.values():
        entry["cached_at"] = time.time() - (_CACHE_FRESHNESS_SECONDS + 1)

    loaded = load_session("sess-resil", client=BrokenFirestore())
    assert loaded is not None
    assert loaded["turns"] == [{"turn": 1}]


def test_save_survives_a_firestore_outage():
    """The current request must still succeed (degraded to single-instance)."""
    save_session("sess-resil-2", {"turns": []}, client=BrokenFirestore())
    assert "sess-resil-2" in _LOCAL_SESSION_CACHE


def test_default_client_is_none_under_pytest():
    """Guards the offline-by-default property: a test that forgets to inject a
    client must not reach real Firestore."""
    assert firestore_session._default_client() is None


# ---------------------------------------------------------------------------
# ĐỢT 16 #4: transactional reflection claim
# ---------------------------------------------------------------------------


class _TxnDoc(FakeDoc):
    """FakeDoc plus the two methods a Firestore transaction needs."""

    def get(self, transaction=None) -> "_TxnDoc":  # noqa: ARG002 -- signature parity
        return self

    def update(self, changes: dict) -> None:
        current = self._store.get(self._id)
        if current is None:
            raise KeyError(self._id)
        merged = copy.deepcopy(current)
        merged.update(copy.deepcopy(changes))
        self._store[self._id] = merged


class _TxnCollection(FakeCollection):
    def document(self, doc_id: str) -> _TxnDoc:
        return _TxnDoc(self._store, doc_id)


class TxnFirestore(FakeFirestore):
    """Fake whose `transactional` decorator serializes the whole closure, which
    is the guarantee a real Firestore transaction gives us: the read, the
    decision and the write cannot be split by another request."""

    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()

    def collection(self, name: str) -> _TxnCollection:
        assert name == "debate_sessions"
        return _TxnCollection(self.store)

    def transaction(self):
        return self

    # Real firestore.Transaction.update() takes (document_reference, field_updates).
    def update(self, doc_ref, changes: dict) -> None:
        doc_ref.update(changes)


@pytest.fixture
def txn_db(monkeypatch):
    db = TxnFirestore()

    def _transactional(fn):
        def _wrapped(transaction):
            with db.lock:
                return fn(transaction)

        return _wrapped

    monkeypatch.setattr("google.cloud.firestore.transactional", _transactional)
    return db


def test_concurrent_reflection_claims_yield_exactly_one_winner(txn_db):
    """ĐỢT 16 #4 -- ADR-022 / README claimed the reflection flag "prevents
    double-click race condition exploits". It did not: the claim was a
    read-then-write, so two POSTs on two Cloud Run instances both read
    `has_reflected=False`, both proceeded, and both banked a growth bonus.

    Two threads race for the same finished session; exactly one may win.
    """
    txn_db.store["sess-race"] = {"completed": True, "student_id": "c1_stu01", "turns": [1, 2, 3]}

    results: list[str] = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()  # maximise the overlap
        status, _ = firestore_session.claim_reflection_atomically("sess-race", client=txn_db)
        results.append(status)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == ["already", "claimed"], f"both requests claimed the reflection: {results}"
    assert txn_db.store["sess-race"]["has_reflected"] is True


def test_reflection_claim_rejects_an_unfinished_debate_inside_the_transaction(txn_db):
    """The `completed` check must live INSIDE the transaction; checking it
    outside would re-open the same split-decision window the claim closes."""
    txn_db.store["sess-open"] = {"completed": False, "turns": [1]}

    status, _ = firestore_session.claim_reflection_atomically("sess-open", client=txn_db)

    assert status == "not_complete"
    assert "has_reflected" not in txn_db.store["sess-open"]


def test_reflection_claim_reports_a_missing_session(txn_db):
    status, data = firestore_session.claim_reflection_atomically("sess-nope", client=txn_db)
    assert status == "missing"
    assert data is None
