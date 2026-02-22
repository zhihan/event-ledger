"""HTTP API for Event Ledger — deployed to Cloud Run."""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel

import firestore_storage
from committer import commit_memory_firestore

app = FastAPI(title="Event Ledger API")

API_KEY = os.environ.get("EVENT_LEDGER_API_KEY", "")
USER_ID = os.environ.get("EVENT_LEDGER_USER_ID", "default")


def _check_auth(authorization: str = Header(...)) -> None:
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


class CreateMemoryRequest(BaseModel):
    message: str
    attachments: list[str] | None = None


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
    return {
        "action": result.action,
        "id": result.doc_id,
        "memory": result.memory.to_dict(),
    }


@app.get("/memories", dependencies=[Depends(_check_auth)])
def list_memories():
    pairs = firestore_storage.load_memories(USER_ID)
    return {
        "memories": [
            {"id": doc_id, **mem.to_dict()}
            for doc_id, mem in pairs
        ],
    }


@app.delete("/memories/{memory_id}", dependencies=[Depends(_check_auth)])
def delete_memory(memory_id: str):
    firestore_storage.delete_memory(memory_id)
    return {"ok": True}
