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
  - The bucket state is **per process**, and this service is deployed with
    `--max-instances 5`. So the honest service-wide ceiling is not `capacity`
    but 5 x `capacity`. Stated as the arithmetic rather than as a vague
    weakness, for the debate policy that is:

        burst      5 instances x 10 tokens          =  50 requests
        sustained  5 instances x 0.2 tokens/second  =   1 request/second

    One request per second of sustained Gemini-backed traffic is a real,
    bounded cost ceiling -- roughly 86k requests/day worst case rather than
    "as fast as curl can loop". It is 5x weaker than the per-instance numbers
    suggest, which is exactly why the multiplier is written out here.

    ĐỢT 17 review note: an external reviewer argued this makes the limiter
    "meaningless under autoscaling, and you chose --max-instances 5 yourself".
    Half right, and worth recording both halves. The contradiction is real --
    we opted into the horizontal scaling that weakens this control. But a 5x
    multiplier on a bounded ceiling is still a bounded ceiling; "meaningless"
    describes no ceiling at all, which is what existed before ADR-017. The
    correct production answer remains Cloud Armor / API Gateway in front, and
    is deliberately out of scope here (see README, Architectural Limitations).
  - Keying is by client IP, taken from the **last** entry of `X-Forwarded-For`
    (Cloud Run appends the real client address, so earlier entries are
    caller-supplied and forgeable -- see `client_key()`), with a fallback to
    the socket peer. What this stops is a flood from one source. A determined
    attacker with many genuine source addresses (a botnet) is not stopped by
    this, and neither is one spread across enough instances.
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
# ĐỢT 27 / ADR-032: deliberately loosened from (5, 0.1) to (15, 0.5) so a judge
# exploring both portals over a month-long window is not locked out mid-review.
#
# Why this does not weaken the system (reviewed Wave 27, and the reasoning is
# the point -- not the numbers):
#   * login() is pure in-process work -- hmac.compare_digest + create_access_token.
#     No Firestore read, no LLM call, no network I/O. Raising its ceiling adds
#     ZERO Vertex AI spend, which is what ADR-017 exists to bound.
#   * Both passcodes are published in the README on purpose (ADR-025), so this
#     bucket was never protecting a secret. It bounds abuse volume, not access.
#   * The expensive surface is a DIFFERENT bucket: DEBATE_POLICY above, used by
#     `debate_limiter` for the five debate routes and /api/parent-note. It is
#     unchanged. A token obtained faster still meets those buckets downstream,
#     and an attacker only ever needed one token anyway -- login rate was never
#     the control on downstream cost.
# Sustained rate goes 6/min -> 30/min per key per process; the bucket, the
# bounded key set, and the last-hop X-Forwarded-For keying (ADR-026) all stay.
LOGIN_POLICY = RateLimitPolicy(capacity=15, refill_per_second=0.5)


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

    ĐỢT 17 #1 -- this function previously took the FIRST entry of
    X-Forwarded-For, with a docstring asserting that the proxy appends and so
    "later entries are attacker-supplied". That was backwards, and it made the
    whole limiter bypassable with one header.

    Cloud Run terminates TLS at its proxy and **appends** the real client
    address to whatever X-Forwarded-For the caller sent. So the header is
    `<anything the client made up>, ..., <real client IP>`: the LAST entry is
    the only one the infrastructure vouches for, and every earlier entry is
    fully attacker-controlled. Keying on the first entry meant an attacker
    sending a different random `X-Forwarded-For` per request got a brand-new
    full bucket every time -- verified against the live service, where 8/8
    requests with random spoofed values passed while the real bucket was
    drained (ADR-026; see README.md).

    Falls back to the socket peer when there is no proxy (local runs).

    NOTE ON SCOPE: taking the last entry is correct for exactly one trusted
    proxy in front of the app, which is what Cloud Run is. If this service is
    ever placed behind an additional proxy (Cloud Armor, an external LB, a
    CDN), the trusted entry moves and this function must move with it --
    counting from the right by a known hop count, never from the left.
    """
    if x_forwarded_for:
        # Right-most non-empty entry: the hop Cloud Run itself recorded.
        for candidate in reversed(x_forwarded_for.split(",")):
            candidate = candidate.strip()
            if candidate:
                return candidate
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
