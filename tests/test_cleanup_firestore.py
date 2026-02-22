"""Tests for Firestore-based cleanup."""

from datetime import date
from unittest.mock import patch, MagicMock

from memory import Memory
from cleanup import cleanup_firestore


def _make_memory(**kwargs) -> Memory:
    defaults = dict(
        target=date(2026, 2, 1),
        expires=date(2026, 2, 15),
        content="old event",
        title="Old",
        user_id="alice",
    )
    defaults.update(kwargs)
    return Memory(**defaults)


@patch("cleanup.purge_attachments")
@patch("firestore_storage.delete_expired")
def test_cleanup_firestore_purges_and_deletes(mock_delete_expired, mock_purge):
    expired_mem = _make_memory(
        attachments=["https://storage.googleapis.com/bucket/a.png"],
    )
    mock_delete_expired.return_value = [("doc1", expired_mem)]

    deleted = cleanup_firestore(today=date(2026, 3, 1))

    assert deleted == ["doc1"]
    mock_purge.assert_called_once_with(expired_mem)


@patch("cleanup.purge_attachments")
@patch("firestore_storage.delete_expired")
def test_cleanup_firestore_no_expired(mock_delete_expired, mock_purge):
    mock_delete_expired.return_value = []

    deleted = cleanup_firestore(today=date(2026, 1, 1))

    assert deleted == []
    mock_purge.assert_not_called()
