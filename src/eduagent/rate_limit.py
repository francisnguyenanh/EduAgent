"""In-process token-bucket rate limiter (ĐỢT 12 NHÓM 2, ADR-017).

WHY THIS EXISTS: `docs/data_lifecycle_and_privacy.md`'s STRIDE table listed
"Token bucket rate limiting" as the Denial-of-Service mitigation. The ĐỢT 12
audit grepped for it and found nothing -- `grep -rniE "rate.?limit|token.?bucket|
slowapi|throttl" src/` returned zero results. The claim was false, and it was
false in a security table, which is the worst place for a claim to be false.

Rather than delete the claim, the mechanism is implemented here, because the
exposure it describes is real: the student-facing debate endpoints each trigger
several Gemini calls, and before ĐỢT 12 they were unauthenticated on a public
URL. A `while true; do curl ...; done` loop was a direct route to draining the
project's Vertex AI quota (a cost-DoS), with no per-caller ceiling anywhere in
the stack.

HONEST SCOPE -- read this before citing it as a mitigation:
  - The bucket state is **per process**. Cloud Run runs N instances, so the
    effective ceiling is N x `capacity`, not `capacity`. This raises the cost
    of an attack and stops casual abuse; it is not a distributed rate limiter.
    A real deployment puts Cloud Armor / API Gateway in front instead.
  - Keying is by client IP, taken from `X-Forwarded-For` (Cloud Run's proxy
    sets it) with a fallback to the socket peer. A determined attacker with
    many source addresses is not stopped by this.
  - State is bounded (`_MAX_TRACKED_KEYS`) so the limiter cannot itself become
    a memory-exhaustion vector when hit from many distinct addresses.

The algorithm is a standard token bucket: each key holds up to `capacity`
tokens, refilled continuously at `refill_per_second`. A request consumes one
token; if the bucket is empty the request is rejected and told how long to
wait. Bursts up to `capacity` are allowed, which is what a real student
clicking through a 3-turn debate looks like, while a sustained flood settles
to `refill_per_second`.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

# Beyond this many distinct keys, the least-recently-seen entries are dropped.
# Dropping a key is fail-open for that caller (they get a fresh full bucket),
# which is the correct trade-off here: the limiter protects against cost
# blowout, and must never become the outage it was added to prevent.
_MAX_TRACKED_KEYS = 10_000


@dataclass(frozen=True)
class RateLimitPolicy:
    """`capacity` tokens, refilled at `refill_per_second`.

    Defaults are tuned for the debate endpoints: a burst of 10 covers a student
    starting an essay and stepping through all 3 turns (plus retries and a
    reflection) without ever seeing a limit, while the sustained ceiling of 1
    request every 5 seconds makes a curl loop cost ~12 Gemini-backed requests
    per minute per instance instead of thousands.
    """

    capacity: int = 10
    refill_per_second: float = 0.2


DEBATE_POLICY = RateLimitPolicy(capacity=10, refill_per_second=0.2)
# Login is cheap (no LLM call) but is the brute-force surface for the shared
# demo password, so it gets a tighter sustained rate and a smaller burst.
LOGIN_POLICY = RateLimitPolicy(capacity=5, refill_per_second=0.1)


class RateLimitExceeded(Exception):
    """Raised when a caller has no tokens left. `retry_after_seconds` is
    surfaced to the caller as an HTTP `Retry-After` header."""

    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = max(1, int(retry_after_seconds + 0.999))
        super().__init__(f"Rate limit exceeded; retry in {self.retry_after_seconds}s.")


class TokenBucketLimiter:
    def __init__(self, policy: RateLimitPolicy) -> None:
        self._policy = policy
        self._lock = threading.Lock()
        # key -> (tokens_remaining, last_refill_monotonic)
        self._buckets: dict[str, tuple[float, float]] = {}

    def check(self, key: str, *, now: float | None = None) -> None:
        """Consumes one token for `key`, or raises RateLimitExceeded.

        `now` is injectable so tests can advance time deterministically instead
        of sleeping -- a rate limiter whose tests sleep is a rate limiter whose
        tests get deleted for being slow.
        """
        now = time.monotonic() if now is None else now
        policy = self._policy

        with self._lock:
            tokens, last_seen = self._buckets.get(key, (float(policy.capacity), now))
            # Refill for the elapsed time, capped at capacity.
            tokens = min(float(policy.capacity), tokens + (now - last_seen) * policy.refill_per_second)

            if tokens < 1.0:
                # Store the refilled state even on rejection, so a rejected
                # caller still accrues tokens and is not locked out forever.
                self._buckets[key] = (tokens, now)
                raise RateLimitExceeded((1.0 - tokens) / policy.refill_per_second)

            self._buckets[key] = (tokens - 1.0, now)
            self._evict_if_needed(now)

    def _evict_if_needed(self, now: float) -> None:
        """Called with the lock held. Drops the oldest half once the tracked-key
        cap is hit, rather than one entry at a time, so eviction is amortised
        instead of running on every request at steady state."""
        if len(self._buckets) <= _MAX_TRACKED_KEYS:
            return
        by_age = sorted(self._buckets.items(), key=lambda kv: kv[1][1])
        for key, _state in by_age[: len(by_age) // 2]:
            self._buckets.pop(key, None)

    def reset(self) -> None:
        """Test helper -- clears all buckets."""
        with self._lock:
            self._buckets.clear()


debate_limiter = TokenBucketLimiter(DEBATE_POLICY)
login_limiter = TokenBucketLimiter(LOGIN_POLICY)


def client_key(*, x_forwarded_for: str | None, peer_host: str | None) -> str:
    """Derives the rate-limit key from a request.

    Cloud Run terminates TLS at its proxy, so the socket peer is the proxy, not
    the caller -- the real client address is the FIRST entry of
    X-Forwarded-For (the proxy appends, so later entries are attacker-supplied
    and must not be trusted). Falls back to the socket peer for local runs
    where no proxy is involved.
    """
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    return peer_host or "unknown"


__all__ = [
    "DEBATE_POLICY",
    "LOGIN_POLICY",
    "RateLimitExceeded",
    "RateLimitPolicy",
    "TokenBucketLimiter",
    "client_key",
    "debate_limiter",
    "login_limiter",
]
