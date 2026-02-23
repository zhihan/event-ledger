#!/usr/bin/env python3
"""One-time migration: assign an owner to legacy pages that have no owner_uids.

After the page-ownership model was introduced (PR #40), existing pages may have
been created without ``owner_uids``.  This script finds those ownerless pages
and assigns the specified Firebase Auth UID as the sole owner.

Usage:
    python scripts/migrate_page_ownership.py --owner-uid <FIREBASE_UID>
    python scripts/migrate_page_ownership.py --owner-uid <FIREBASE_UID> --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from the repo root without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import page_storage  # noqa: E402


def migrate_page_ownership(owner_uid: str, *, dry_run: bool = False) -> list[str]:
    """Assign *owner_uid* to every page that currently has no owners.

    Returns the list of page slugs that were (or would be) updated.
    """
    ownerless = page_storage.list_ownerless_pages()
    if not ownerless:
        print("No ownerless pages found — nothing to do.")
        return []

    updated: list[str] = []
    for page in ownerless:
        if dry_run:
            print(f"[dry-run] Would assign owner {owner_uid} to page '{page.slug}'")
        else:
            page_storage.update_page(page.slug, {"owner_uids": [owner_uid]})
            page_storage.write_audit_log(
                page_slug=page.slug,
                action="owner_added",
                actor_uid=owner_uid,
                target_uid=owner_uid,
                metadata={"reason": "legacy_migration"},
            )
            print(f"Assigned owner {owner_uid} to page '{page.slug}'")
        updated.append(page.slug)

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assign an owner to legacy pages that have no owner_uids",
    )
    parser.add_argument(
        "--owner-uid", required=True,
        help="Firebase Auth UID to assign as page owner",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be changed without writing to Firestore",
    )
    args = parser.parse_args()

    updated = migrate_page_ownership(args.owner_uid, dry_run=args.dry_run)
    label = "would be " if args.dry_run else ""
    print(f"\nTotal: {len(updated)} page(s) {label}updated.")


if __name__ == "__main__":
    main()
