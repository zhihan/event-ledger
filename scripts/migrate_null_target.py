#!/usr/bin/env python3
"""One-time migration: fix legacy memory documents that have target=null.

Before target became required, "ongoing" events were stored with target=null
and expires set to the coming Sunday.  This script finds those documents and
sets target to the Saturday of the same week (the day before expires, when
expires is a Sunday), making them compatible with the current data model.

Usage:
    python scripts/migrate_null_target.py
    python scripts/migrate_null_target.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from firestore_storage import _get_client  # noqa: E402


def _target_from_expires(expires: date) -> date:
    """Derive a target date from the legacy expires date.

    Ongoing events had expires = coming Sunday.  We convert that to the
    Saturday of the same week (expires - 1 day).  For any other expiry
    day, we use expires itself as a safe fallback.
    """
    if expires.isoweekday() == 7:  # Sunday
        return expires - timedelta(days=1)
    return expires


def migrate_null_targets(*, dry_run: bool = False) -> list[str]:
    """Set target on all memory documents that have target=null.

    Returns the list of document IDs that were (or would be) updated.
    """
    db = _get_client()
    updated: list[str] = []

    for doc in db.collection("memories").stream():
        data = doc.to_dict() or {}
        if data.get("target") is not None:
            continue  # already has a target

        raw_expires = data.get("expires")
        if not raw_expires:
            print(f"[SKIP] {doc.id}: missing expires, skipping")
            continue

        expires = date.fromisoformat(raw_expires) if isinstance(raw_expires, str) else raw_expires
        target = _target_from_expires(expires)

        if dry_run:
            print(f"[dry-run] {doc.id}: would set target={target} (expires={expires})")
        else:
            doc.reference.update({"target": target.isoformat()})
            print(f"[updated] {doc.id}: target={target} (expires={expires})")

        updated.append(doc.id)

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set target on legacy memory documents that have target=null",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be changed without writing to Firestore",
    )
    args = parser.parse_args()

    updated = migrate_null_targets(dry_run=args.dry_run)
    label = "would be " if args.dry_run else ""
    print(f"\nTotal: {len(updated)} document(s) {label}updated.")


if __name__ == "__main__":
    main()
