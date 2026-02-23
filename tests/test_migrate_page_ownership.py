"""Tests for the page ownership migration script."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

import page_storage
from page_storage import Page

# Import the migration function — the script adds src/ to sys.path itself,
# but in tests we already have it on the path via conftest/pytest config.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from migrate_page_ownership import migrate_page_ownership  # noqa: E402


OWNER_UID = "firebase-uid-abc123"


class TestListOwnerlessPages:
    @patch("page_storage._get_client")
    def test_returns_pages_without_owners(self, mock_gc):
        mock_db = MagicMock()
        mock_gc.return_value = mock_db

        doc_with_owners = MagicMock()
        doc_with_owners.id = "owned-page"
        doc_with_owners.to_dict.return_value = {
            "title": "Owned", "visibility": "public", "owner_uids": ["u1"],
        }

        doc_without_owners = MagicMock()
        doc_without_owners.id = "legacy-page"
        doc_without_owners.to_dict.return_value = {
            "title": "Legacy", "visibility": "public", "owner_uids": [],
        }

        doc_missing_field = MagicMock()
        doc_missing_field.id = "old-page"
        doc_missing_field.to_dict.return_value = {
            "title": "Old", "visibility": "public",
            # no owner_uids field at all
        }

        mock_db.collection.return_value.stream.return_value = [
            doc_with_owners, doc_without_owners, doc_missing_field,
        ]

        result = page_storage.list_ownerless_pages()
        slugs = [p.slug for p in result]
        assert "legacy-page" in slugs
        assert "old-page" in slugs
        assert "owned-page" not in slugs

    @patch("page_storage._get_client")
    def test_returns_empty_when_all_owned(self, mock_gc):
        mock_db = MagicMock()
        mock_gc.return_value = mock_db

        doc = MagicMock()
        doc.id = "my-page"
        doc.to_dict.return_value = {
            "title": "My Page", "visibility": "public", "owner_uids": ["u1"],
        }
        mock_db.collection.return_value.stream.return_value = [doc]

        result = page_storage.list_ownerless_pages()
        assert result == []


class TestMigratePageOwnership:
    @patch("migrate_page_ownership.page_storage.write_audit_log")
    @patch("migrate_page_ownership.page_storage.update_page")
    @patch("migrate_page_ownership.page_storage.list_ownerless_pages")
    def test_assigns_owner_to_ownerless_pages(self, mock_list, mock_update, mock_audit):
        legacy = Page(slug="cambridge-lexington", title="Legacy", visibility="public", owner_uids=[])
        mock_list.return_value = [legacy]
        mock_update.return_value = Page(
            slug="cambridge-lexington", title="Legacy", visibility="public",
            owner_uids=[OWNER_UID],
        )

        result = migrate_page_ownership(OWNER_UID)

        assert result == ["cambridge-lexington"]
        mock_update.assert_called_once_with(
            "cambridge-lexington", {"owner_uids": [OWNER_UID]},
        )
        mock_audit.assert_called_once()
        audit_kwargs = mock_audit.call_args
        assert audit_kwargs.kwargs["action"] == "owner_added"
        assert audit_kwargs.kwargs["actor_uid"] == OWNER_UID
        assert audit_kwargs.kwargs["metadata"]["reason"] == "legacy_migration"

    @patch("migrate_page_ownership.page_storage.write_audit_log")
    @patch("migrate_page_ownership.page_storage.create_page")
    @patch("migrate_page_ownership.page_storage.get_page")
    @patch("migrate_page_ownership._legacy_page_slugs_from_memories")
    @patch("migrate_page_ownership.page_storage.list_ownerless_pages")
    def test_creates_pages_from_legacy_memories_when_no_pages_exist(
        self,
        mock_list_ownerless,
        mock_legacy_slugs,
        mock_get_page,
        mock_create_page,
        mock_audit,
    ):
        mock_list_ownerless.return_value = []
        mock_legacy_slugs.return_value = ["cambridge-lexington"]
        mock_get_page.return_value = None

        result = migrate_page_ownership(OWNER_UID)

        assert result == ["cambridge-lexington"]
        mock_create_page.assert_called_once()
        created_page = mock_create_page.call_args.args[0]
        assert created_page.slug == "cambridge-lexington"
        assert created_page.owner_uids == [OWNER_UID]
        assert created_page.visibility == "public"
        # audit called for page_created
        assert mock_audit.called
        assert any(c.kwargs.get("action") == "page_created" for c in mock_audit.call_args_list)

    @patch("migrate_page_ownership.page_storage.write_audit_log")
    @patch("migrate_page_ownership.page_storage.update_page")
    @patch("migrate_page_ownership.page_storage.list_ownerless_pages")
    def test_dry_run_does_not_write(self, mock_list, mock_update, mock_audit):
        legacy = Page(slug="legacy", title="Legacy", visibility="public", owner_uids=[])
        mock_list.return_value = [legacy]

        result = migrate_page_ownership(OWNER_UID, dry_run=True)

        assert result == ["legacy"]
        mock_update.assert_not_called()
        mock_audit.assert_not_called()

    @patch("migrate_page_ownership._legacy_page_slugs_from_memories")
    @patch("migrate_page_ownership.page_storage.list_ownerless_pages")
    def test_no_ownerless_pages(self, mock_list, mock_legacy_slugs):
        mock_list.return_value = []
        mock_legacy_slugs.return_value = []

        result = migrate_page_ownership(OWNER_UID)
        assert result == []

    @patch("migrate_page_ownership.page_storage.write_audit_log")
    @patch("migrate_page_ownership.page_storage.update_page")
    @patch("migrate_page_ownership.page_storage.list_ownerless_pages")
    def test_multiple_ownerless_pages(self, mock_list, mock_update, mock_audit):
        pages = [
            Page(slug="page-a", title="A", visibility="public", owner_uids=[]),
            Page(slug="page-b", title="B", visibility="public", owner_uids=[]),
        ]
        mock_list.return_value = pages
        mock_update.return_value = pages[0]  # return value not critical

        result = migrate_page_ownership(OWNER_UID)

        assert result == ["page-a", "page-b"]
        assert mock_update.call_count == 2
        assert mock_audit.call_count == 2
