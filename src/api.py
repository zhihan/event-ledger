"""HTTP API for Small Group — deployed to Cloud Run.

This is the application entry point. It owns infrastructure concerns:
CORS, request logging, the /api prefix-stripping middleware for Firebase
Hosting rewrites, exception handlers, and the health check endpoint.

All business-logic routes live in api_v2.py and are mounted here via
include_router. There is no longer a v1 router; api_v2.py is the sole
router.
"""

from __future__ import annotations

import json
import logging
import sys
import time

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

_LEVEL_TO_SEVERITY = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}

# Standard LogRecord attributes to exclude from the JSON payload.
_STANDARD_ATTRS = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "thread", "threadName", "taskName",
})


class _CloudJsonFormatter(logging.Formatter):
    """Emit log records as Cloud Logging-compatible structured JSON.

    Cloud Run captures stdout JSON lines and makes every top-level key a
    searchable field in Log Explorer.  The special keys `httpRequest` and
    `logging.googleapis.com/trace` get first-class UI treatment.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "severity": _LEVEL_TO_SEVERITY.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
        }
        for key, val in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_"):
                continue
            # Rename `trace` → the GCP structured-log trace key.
            entry["logging.googleapis.com/trace" if key == "trace" else key] = val
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_CloudJsonFormatter())
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_root.handlers.clear()
_root.addHandler(_handler)

logger = logging.getLogger(__name__)

app = FastAPI(title="Small Group API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v2 router (rooms, series, occurrences, check-ins)
from api_v2 import router as v2_router  # noqa: E402
app.include_router(v2_router)


class StripApiPrefixMiddleware:
    """Allow Firebase Hosting /api/** rewrites without requiring separate routes.

    Firebase Hosting forwards requests to Cloud Run with the original path, e.g.
    `/api/pages/foo`. The backend historically serves `/pages/foo`.

    This middleware strips a leading `/api` prefix so both paths work.
    """

    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path") or ""
            if path == "/api":
                scope = dict(scope)
                scope["path"] = "/"
            elif path.startswith("/api/"):
                scope = dict(scope)
                scope["path"] = path[len("/api"):]
        await self.inner_app(scope, receive, send)


# Must be installed before routing.
app.add_middleware(StripApiPrefixMiddleware)


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)

    extra: dict = {
        "httpRequest": {
            "requestMethod": request.method,
            "requestUrl": request.url.path,
            "status": response.status_code,
            "latency": f"{duration_ms / 1000:.3f}s",
        }
    }
    trace_header = request.headers.get("x-cloud-trace-context")
    if trace_header:
        extra["trace"] = trace_header.split("/")[0]

    logger.info("%s %s %d", request.method, request.url.path, response.status_code, extra=extra)
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = await request.body()
    logger.error(
        "Validation error %s %s",
        request.method, request.url.path,
        extra={
            "requestBody": body.decode("utf-8", errors="replace"),
            "validationErrors": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert ValueError from storage layer to 400 Bad Request."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/_healthz")
@app.get("/healthz")
def healthz():
    return {"ok": True}
