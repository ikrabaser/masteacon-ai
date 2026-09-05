"""FastAPI application entrypoint."""
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi.responses import JSONResponse

from app.api.routes import agent, auth, conversations, documents, health, observability, rag, search, workspaces
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.production_config import validate_production_config
from app.core.request_context import set_request_id

settings = get_settings()
configure_logging(debug=settings.debug)
logger = get_logger(__name__)

_production_config_errors = validate_production_config(settings)
if _production_config_errors:
    # Refuse to boot with an insecure or incomplete production configuration —
    # serving traffic in that state is worse than not starting at all. See
    # app/core/production_config.py for the full list of checks.
    raise RuntimeError(
        "Refusing to start with APP_ENV=production due to configuration problems:\n- "
        + "\n- ".join(_production_config_errors)
    )

app = FastAPI(
    title=settings.app_name,
    description="Upload documents and ask questions about them using Retrieval-Augmented Generation.",
    version="0.1.0",
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns (or propagates) a request correlation id for structured logging.

    Every log line emitted while handling a request — no matter which service
    or repository logs it — is automatically tagged with this id (see
    app.core.request_context / app.core.logging.JsonFormatter), and it's
    echoed back as a response header so a client can report it for support.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        set_request_id(request_id)
        started_at = time.perf_counter()

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "Handled request",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        return response


app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(rag.router)
app.include_router(conversations.router)
app.include_router(agent.router)
app.include_router(observability.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Translate domain errors into clean HTTP responses without leaking internals."""
    logger.warning("Handled application error: %s", exc.message)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/")
async def root() -> dict[str, str]:
    """Basic application info."""
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "docs": "/docs",
    }
