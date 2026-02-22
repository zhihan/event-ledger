"""Tests for the HTTP API."""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from memory import Memory
from committer import CommitResult


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("EVENT_LEDGER_API_KEY", "test-key")
    monkeypatch.setenv("EVENT_LEDGER_USER_ID", "test-user")
    # Re-import to pick up env vars
    import api
    api.API_KEY = "test-key"
    api.USER_ID = "test-user"


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


AUTH = {"Authorization": "Bearer test-key"}


# --- Auth tests ---

def test_healthz_no_auth(client):
    resp = client.get("/_healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_healthz_legacy_alias(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_list_memories_no_auth(client):
    resp = client.get("/memories")
    assert resp.status_code == 422  # missing header


def test_list_memories_bad_key(client):
    resp = client.get("/memories", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_create_memory_no_auth(client):
    resp = client.post("/memories", json={"message": "hi"})
    assert resp.status_code == 422


def test_create_memory_bad_key(client):
    resp = client.post("/memories", json={"message": "hi"},
                       headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


# --- POST /memories ---

@patch("api.commit_memory_firestore")
def test_create_memory(mock_commit, client):
    mem = Memory(
        target=date(2026, 3, 5),
        expires=date(2026, 4, 4),
        content="Weekly planning session",
        title="Team Meeting",
        time="10:00",
        place="Room A",
        user_id="test-user",
    )
    mock_commit.return_value = CommitResult(
        action="created", doc_id="abc123", memory=mem,
    )

    resp = client.post("/memories", json={"message": "Team meeting Thursday 10am"},
                       headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "created"
    assert data["id"] == "abc123"
    assert data["memory"]["title"] == "Team Meeting"

    mock_commit.assert_called_once_with(
        message="Team meeting Thursday 10am",
        user_id="test-user",
        attachment_urls=None,
    )


@patch("api.commit_memory_firestore")
def test_create_memory_with_attachments(mock_commit, client):
    mem = Memory(
        target=date(2026, 3, 5), expires=date(2026, 4, 4),
        content="Event", title="Test", user_id="test-user",
    )
    mock_commit.return_value = CommitResult(
        action="created", doc_id="xyz", memory=mem,
    )

    resp = client.post("/memories",
                       json={"message": "hi", "attachments": ["https://example.com/a.png"]},
                       headers=AUTH)
    assert resp.status_code == 200
    mock_commit.assert_called_once_with(
        message="hi",
        user_id="test-user",
        attachment_urls=["https://example.com/a.png"],
    )


# --- GET /memories ---

@patch("api.firestore_storage")
def test_list_memories(mock_fs, client):
    mem = Memory(
        target=date(2026, 3, 5), expires=date(2026, 4, 4),
        content="Hello", title="Test Event", user_id="test-user",
    )
    mock_fs.load_memories.return_value = [("doc1", mem)]

    resp = client.get("/memories", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["memories"]) == 1
    assert data["memories"][0]["id"] == "doc1"
    assert data["memories"][0]["title"] == "Test Event"


# --- DELETE /memories/{id} ---

@patch("api.firestore_storage")
def test_delete_memory(mock_fs, client):
    resp = client.delete("/memories/doc1", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    mock_fs.delete_memory.assert_called_once_with("doc1")
