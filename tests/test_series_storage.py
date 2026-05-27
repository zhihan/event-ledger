"""Tests for series_storage.py using mocked Firestore."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from series_storage import OCCURRENCES_COLLECTION, SERIES_COLLECTION, delete_series


def _mock_doc(doc_id: str):
    doc = MagicMock()
    doc.id = doc_id
    return doc


class TestDeleteSeries:
    def test_deletes_child_occurrences_before_series(self):
        mock_db = MagicMock()
        mock_series_ref = MagicMock()
        mock_occurrence_query = MagicMock()
        mock_occurrence_query.stream.return_value = [
            _mock_doc("occ-1"),
            _mock_doc("occ-2"),
        ]

        def collection(name: str):
            col = MagicMock()
            if name == OCCURRENCES_COLLECTION:
                col.where.return_value = mock_occurrence_query
            elif name == SERIES_COLLECTION:
                col.document.return_value = mock_series_ref
            return col

        mock_db.collection.side_effect = collection

        with (
            patch("series_storage._get_client", return_value=mock_db),
            patch("series_storage.delete_occurrence") as mock_delete_occurrence,
        ):
            delete_series("s-1")

        mock_db.collection.assert_any_call(OCCURRENCES_COLLECTION)
        mock_delete_occurrence.assert_has_calls([call("occ-1"), call("occ-2")])
        mock_series_ref.delete.assert_called_once_with()
