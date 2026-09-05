"""Unit tests for UsageGuardService against a minimal in-memory fake Redis
client — exercises the real rate-limit/concurrency logic (unlike route tests,
which use FakeUsageGuardService's interface stub instead).
"""
import pytest
from redis.exceptions import RedisError

from app.services.usage_guard_service import ConcurrencyLimitExceeded, UsageGuardService


class _FakePipeline:
    def __init__(self, client: "_FakeRedisClient") -> None:
        self._client = client
        self._ops: list[tuple[str, str]] = []

    def incr(self, key: str):
        self._ops.append(("incr", key))
        return self

    def ttl(self, key: str):
        self._ops.append(("ttl", key))
        return self

    async def execute(self):
        if self._client.raise_error:
            raise RedisError("simulated failure")
        results = []
        for op, key in self._ops:
            if op == "incr":
                self._client.store[key] = self._client.store.get(key, 0) + 1
                results.append(self._client.store[key])
            elif op == "ttl":
                results.append(self._client.ttls.get(key, -1))
        return results


class _FakeRedisClient:
    """Enough of redis.asyncio.Redis's surface for UsageGuardService."""

    def __init__(self, raise_error: bool = False) -> None:
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.raise_error = raise_error

    def pipeline(self, transaction: bool = True):
        return _FakePipeline(self)

    async def incr(self, key: str) -> int:
        if self.raise_error:
            raise RedisError("simulated failure")
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def decr(self, key: str) -> int:
        if self.raise_error:
            raise RedisError("simulated failure")
        self.store[key] = self.store.get(key, 0) - 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> None:
        if self.raise_error:
            raise RedisError("simulated failure")
        self.ttls[key] = seconds

    async def set(self, key: str, value: int) -> None:
        if self.raise_error:
            raise RedisError("simulated failure")
        self.store[key] = value


@pytest.mark.asyncio
async def test_allows_requests_under_the_limit() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    for _ in range(3):
        result = await guard.check_rate_limit(scope="ask", identifier="user-1", limit=3, window_seconds=3600)
        assert result.allowed is True


@pytest.mark.asyncio
async def test_rejects_requests_over_the_limit_with_a_retry_after() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    for _ in range(3):
        await guard.check_rate_limit(scope="ask", identifier="user-1", limit=3, window_seconds=3600)

    result = await guard.check_rate_limit(scope="ask", identifier="user-1", limit=3, window_seconds=3600)

    assert result.allowed is False
    assert result.retry_after > 0


@pytest.mark.asyncio
async def test_different_users_do_not_share_a_quota_bucket() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    for _ in range(3):
        await guard.check_rate_limit(scope="ask", identifier="user-1", limit=3, window_seconds=3600)

    # user-1 is now at the limit; user-2 must be completely unaffected.
    result = await guard.check_rate_limit(scope="ask", identifier="user-2", limit=3, window_seconds=3600)

    assert result.allowed is True


@pytest.mark.asyncio
async def test_different_scopes_do_not_share_a_quota_bucket() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    for _ in range(3):
        await guard.check_rate_limit(scope="ask", identifier="user-1", limit=3, window_seconds=3600)

    # Same user, different action - a separate budget.
    result = await guard.check_rate_limit(scope="agent", identifier="user-1", limit=3, window_seconds=3600)

    assert result.allowed is True


@pytest.mark.asyncio
async def test_disabled_guard_always_allows() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=False)

    for _ in range(100):
        result = await guard.check_rate_limit(scope="ask", identifier="user-1", limit=1, window_seconds=3600)
        assert result.allowed is True


@pytest.mark.asyncio
async def test_rate_limit_fails_open_when_redis_is_unavailable() -> None:
    guard = UsageGuardService(_FakeRedisClient(raise_error=True), enabled=True)

    result = await guard.check_rate_limit(scope="ask", identifier="user-1", limit=1, window_seconds=3600)

    assert result.allowed is True


@pytest.mark.asyncio
async def test_concurrency_slot_is_granted_up_to_the_max() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    for _ in range(2):
        await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=2)  # must not raise


@pytest.mark.asyncio
async def test_concurrency_slot_is_refused_once_at_the_max() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=1)

    with pytest.raises(ConcurrencyLimitExceeded):
        await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=1)


@pytest.mark.asyncio
async def test_releasing_a_slot_frees_it_up_for_another_request() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=1)
    await guard.release_concurrency_slot(scope="llm", identifier="user-1")

    await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=1)  # must not raise


@pytest.mark.asyncio
async def test_concurrency_limit_is_per_user() -> None:
    guard = UsageGuardService(_FakeRedisClient(), enabled=True)

    await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=1)

    await guard.acquire_concurrency_slot(scope="llm", identifier="user-2", max_concurrent=1)  # must not raise


@pytest.mark.asyncio
async def test_concurrency_limit_fails_closed_when_redis_is_unavailable() -> None:
    guard = UsageGuardService(_FakeRedisClient(raise_error=True), enabled=True)

    with pytest.raises(ConcurrencyLimitExceeded):
        await guard.acquire_concurrency_slot(scope="llm", identifier="user-1", max_concurrent=10)
