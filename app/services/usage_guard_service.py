"""Rate limiting and concurrency control for expensive, LLM-backed operations.

Kept entirely separate from AuthProtectionService (login/register abuse
protection) — this guards *cost* (LLM API calls, document indexing dispatch)
for an already-authenticated user, not authentication itself. Conflating the
two would mean a burst of legitimate `/ask` traffic could trip the same
mechanism protecting against credential-stuffing, which makes no sense as a
shared budget.

Fail-open vs fail-closed is a deliberate, per-mechanism choice, not one
blanket policy:
- Rate limits (a request quota over a time window) FAIL OPEN when Redis is
  unavailable — the same behavior AuthProtectionService already has. Redis
  being briefly down is an infra blip; refusing all LLM usage app-wide
  because of it is a worse availability trade-off than temporarily not
  enforcing a quota.
- The concurrency limit (how many requests one user has in flight *right
  now*) FAILS CLOSED. Without it, a single user (or a client bug firing
  runaway parallel requests) could exhaust shared backend resources or blow
  through the LLM provider's own rate limit for *every* user — a failure
  that cascades well beyond the one account that caused it. A concurrency
  check that goes blind should refuse work, not wave it through.

Redis keys are built only from ids (user_id, an action name) — never from
request content (a question, a document) — so a Redis dump can never expose
what anyone actually asked or uploaded.
"""
from dataclasses import dataclass
from hashlib import sha256

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int = 0


class ConcurrencyLimitExceeded(Exception):
    """Raised by acquire_concurrency_slot() — caller already has the max in flight,
    or the limiter itself is unavailable (fail-closed)."""


def _key(kind: str, scope: str, identifier: str) -> str:
    digest = sha256(f"{scope}:{identifier}".encode("utf-8")).hexdigest()[:32]
    return f"masteacon:usage:{kind}:{digest}"


class UsageGuardService:
    """Per-identifier (user or workspace) request-rate and concurrency guards."""

    def __init__(self, redis_client: Redis, enabled: bool) -> None:
        self._redis = redis_client
        self._enabled = enabled

    async def check_rate_limit(
        self, *, scope: str, identifier: str, limit: int, window_seconds: int
    ) -> RateLimitResult:
        if not self._enabled:
            return RateLimitResult(allowed=True)

        key = _key("rate", scope, identifier)
        try:
            pipeline = self._redis.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.ttl(key)
            current, ttl = await pipeline.execute()

            if current == 1 or ttl == -1:
                await self._redis.expire(key, window_seconds)
                ttl = window_seconds

            if current > limit:
                return RateLimitResult(allowed=False, retry_after=max(int(ttl), 1))
            return RateLimitResult(allowed=True)
        except RedisError:
            logger.warning(
                "Usage rate limiter unavailable; allowing the request (fail-open).",
                extra={"event": "usage_limiter_unavailable", "scope": scope, "mode": "rate_limit"},
            )
            return RateLimitResult(allowed=True)

    async def acquire_concurrency_slot(
        self, *, scope: str, identifier: str, max_concurrent: int, ttl_seconds: int = 120
    ) -> None:
        """Raises ConcurrencyLimitExceeded if the caller is already at the limit
        (or the limiter is unavailable). Callers MUST release the slot in a
        `finally` block once they're done, even on error.
        """
        if not self._enabled:
            return

        key = _key("concurrency", scope, identifier)
        try:
            current = await self._redis.incr(key)
            if current == 1:
                # Safety net: if the process crashes before releasing, this
                # key still expires instead of permanently consuming a slot.
                await self._redis.expire(key, ttl_seconds)
            if current > max_concurrent:
                await self._redis.decr(key)  # give back the slot this attempt didn't get
                raise ConcurrencyLimitExceeded("Too many concurrent requests.")
        except RedisError:
            logger.error(
                "Concurrency limiter unavailable; refusing the request (fail-closed).",
                extra={"event": "usage_limiter_unavailable", "scope": scope, "mode": "concurrency"},
            )
            raise ConcurrencyLimitExceeded("Concurrency limiter unavailable.") from None

    async def release_concurrency_slot(self, *, scope: str, identifier: str) -> None:
        if not self._enabled:
            return

        key = _key("concurrency", scope, identifier)
        try:
            value = await self._redis.decr(key)
            if value < 0:
                # Never let a stale release (e.g. the TTL safety net already
                # expired the key) push the counter negative.
                await self._redis.set(key, 0)
        except RedisError:
            logger.warning(
                "Could not release a concurrency slot (best-effort only).",
                extra={"event": "usage_limiter_unavailable", "scope": scope, "mode": "concurrency_release"},
            )
