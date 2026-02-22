"""Tests for the publisher module's Firestore path."""

from datetime import date
from unittest.mock import patch

from memory import Memory
from publisher import load_memories_from_firestore


@patch("firestore_storage.load_memories")
def test_load_memories_from_firestore_with_user_id(mock_load):
    mem1 = Memory(target=date(2026, 3, 5), expires=date(2026, 4, 5),
                  content="Event A", title="A", user_id="alice")
    mem2 = Memory(target=date(2026, 3, 1), expires=date(2026, 4, 1),
                  content="Event B", title="B", user_id="alice")
    mock_load.return_value = [("d1", mem1), ("d2", mem2)]

    results = load_memories_from_firestore(date(2026, 2, 18), user_id="alice")

    mock_load.assert_called_once_with("alice", date(2026, 2, 18))
    # Should be sorted by target date
    assert results[0].title == "B"
    assert results[1].title == "A"


@patch("firestore_storage.load_all_memories")
def test_load_memories_from_firestore_all(mock_load_all):
    mem1 = Memory(target=date(2026, 3, 5), expires=date(2026, 4, 5),
                  content="Event A", title="A", user_id="alice")
    expired = Memory(target=date(2026, 1, 1), expires=date(2026, 1, 31),
                     content="Old", title="Old", user_id="bob")
    mock_load_all.return_value = [("d1", mem1), ("d2", expired)]

    results = load_memories_from_firestore(date(2026, 2, 18))

    assert len(results) == 1
    assert results[0].title == "A"


@patch("firestore_storage.load_memories")
def test_load_memories_from_firestore_ongoing_sorts_first(mock_load):
    dated = Memory(target=date(2026, 3, 5), expires=date(2026, 4, 5),
                   content="Dated", title="Dated", user_id="alice")
    ongoing = Memory(target=None, expires=date(2026, 4, 5),
                     content="Ongoing", title="Ongoing", user_id="alice")
    mock_load.return_value = [("d1", dated), ("d2", ongoing)]

    results = load_memories_from_firestore(date(2026, 2, 18), user_id="alice")

    assert results[0].title == "Ongoing"
    assert results[1].title == "Dated"
