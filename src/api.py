"""HTTP API for Event Ledger — deployed to Cloud Run."""

from __future__ import annotations

import logging
import os
import time

from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response
from pydantic import BaseModel

import firestore_storage
from committer import commit_memory_firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Event Ledger API")

API_KEY = os.environ.get("EVENT_LEDGER_API_KEY", "")
USER_ID = os.environ.get("EVENT_LEDGER_USER_ID", "default")


@app.middleware("http")
async def logging_middleware(request: Request, call_next) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)

    extra = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    trace_header = request.headers.get("x-cloud-trace-context")
    if trace_header:
        extra["trace"] = trace_header.split("/")[0]

    logger.info("request %s %s %d %.1fms", extra["method"], extra["path"],
                extra["status_code"], duration_ms, extra=extra)
    return response


def _check_auth(authorization: str = Header(...)) -> None:
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if authorization != f"Bearer {API_KEY}":
        logger.warning("auth_failure", extra={"path": "unknown"})
        raise HTTPException(status_code=401, detail="Invalid API key")


class CreateMemoryRequest(BaseModel):
    message: str
    attachments: list[str] | None = None


@app.get("/_healthz")
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/memories", dependencies=[Depends(_check_auth)])
def create_memory(body: CreateMemoryRequest):
    result = commit_memory_firestore(
        message=body.message,
        user_id=USER_ID,
        attachment_urls=body.attachments,
    )
    logger.info(
        "create_memory action=%s doc_id=%s", result.action, result.doc_id,
        extra={
            "action": result.action,
            "doc_id": result.doc_id,
            "user_id": USER_ID,
            "message_len": len(body.message),
            "num_attachments": len(body.attachments) if body.attachments else 0,
        },
    )
    return {
        "action": result.action,
        "id": result.doc_id,
        "memory": result.memory.to_dict(),
    }


@app.get("/memories", dependencies=[Depends(_check_auth)])
def list_memories():
    pairs = firestore_storage.load_memories(USER_ID)
    logger.info(
        "list_memories user_id=%s count=%d", USER_ID, len(pairs),
        extra={"user_id": USER_ID, "count": len(pairs)},
    )
    return {
        "memories": [
            {"id": doc_id, **mem.to_dict()}
            for doc_id, mem in pairs
        ],
    }


@app.delete("/memories/{memory_id}", dependencies=[Depends(_check_auth)])
def delete_memory(memory_id: str):
    firestore_storage.delete_memory(memory_id)
    logger.info(
        "delete_memory memory_id=%s user_id=%s", memory_id, USER_ID,
        extra={"memory_id": memory_id, "user_id": USER_ID},
    )
    return {"ok": True}
