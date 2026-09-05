"""Liveness/readiness endpoints, split per Kubernetes/Docker convention.

- `/health/live` answers "is the process itself alive" — no dependency checks
  at all. An orchestrator restarting a container on liveness failure should
  never do so just because Postgres or Redis had a blip; that's what
  readiness is for.
- `/health/ready` answers "can this instance actually serve traffic right
  now" — it checks the dependencies a request would actually need
  (PostgreSQL, Redis), and returns 503 if either is unreachable so a load
  balancer can stop routing to it until it recovers.
- `/health` is kept as a plain alias for liveness, for any external monitor
  or existing bookmark already pointed at the historical single endpoint
  (see frontend/nginx.conf.template's proxy).

LLM provider (OpenAI/Anthropic) reachability is deliberately never part of
readiness: those are third-party services outside this deployment's control,
and a transient outage there must not take otherwise-healthy instances out of
rotation or trigger container restarts.
"""
from fastapi import APIRouter, Depends, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.redis import get_redis_client

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """The process can respond to requests at all. No dependency checks."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(
    response: Response,
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> dict[str, object]:
    """Can this instance actually serve traffic — are its real dependencies up."""
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        # This is a public, unauthenticated endpoint — never put exception
        # details (which can include connection strings, hostnames) in the
        # response. Full detail goes to the log, which log-shipping/ops
        # tooling can see; callers just get "unreachable".
        logger.exception("Readiness check: database unreachable")
        checks["database"] = "unreachable"

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Readiness check: redis unreachable")
        checks["redis"] = "unreachable"

    ready = all(status == "ok" for status in checks.values())
    if not ready:
        response.status_code = 503

    return {"status": "ready" if ready else "not_ready", "checks": checks}
