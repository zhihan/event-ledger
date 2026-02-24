"""Cleanup — delete expired memories from Firestore and purge GCS attachments."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from memory import Memory
from storage import delete_from_gcs

logger = logging.getLogger(__name__)


def purge_attachments(mem: Memory) -> None:
    """Delete each attachment URL from GCS."""
    if not mem.attachments:
        return
    for url in mem.attachments:
        try:
            delete_from_gcs(url)
        except Exception:
            logger.warning("Failed to delete attachment: %s", url)


def cleanup_firestore(today: date | None = None) -> list[str]:
    """Delete expired memories from Firestore and purge their GCS attachments.

    Returns a list of deleted Firestore document IDs.
    """
    import firestore_storage

    if today is None:
        today = date.today()

    deleted_pairs = firestore_storage.delete_expired(today)
    for _, mem in deleted_pairs:
        purge_attachments(mem)
    return [doc_id for doc_id, _ in deleted_pairs]


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the cleanup module."""
    parser = argparse.ArgumentParser(
        description="Delete expired memories and purge attachments",
    )
    parser.add_argument(
        "--today", type=date.fromisoformat, default=None,
        help="Override today's date for testing",
    )
    args = parser.parse_args(argv)

    today = args.today or date.today()
    deleted_ids = cleanup_firestore(today)
    for doc_id in deleted_ids:
        print(f"Deleted Firestore doc: {doc_id}")


if __name__ == "__main__":
    main()
