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


def _legacy_page_slugs_from_memories() -> list[str]:
    """Infer legacy page slugs from pre-ownership memory docs.

    Before the page model existed, memories were stored under the top-level
    `memories` collection with a `user_id` field (e.g. "cambridge-lexington").
    When migrating to owned pages, we may need to create `pages/{slug}` docs.

    Returns distinct legacy slugs (sorted) found in memories.
    """
    # Import lazily so scripts can still be imported in tests with mocks.
    from firestore_storage import _get_client  # type: ignore

    db = _get_client()
    slugs: set[str] = set()
    for doc in db.collection("memories").stream():
        data = doc.to_dict() or {}
        slug = data.get("user_id")
        if isinstance(slug, str) and slug:
            slugs.add(slug)
    return sorted(slugs)


def migrate_page_ownership(owner_uid: str, *, dry_run: bool = False) -> list[str]:
    """Migrate legacy installs to the page-ownership model.

    1) Assign *owner_uid* to any existing pages that have empty/missing owners.
    2) If there are no pages but there are legacy memories, create pages inferred
       from legacy `memories.user_id` and set *owner_uid* as owner.

    Returns the list of page slugs that were (or would be) updated/created.
    """
    updated: list[str] = []

    ownerless = page_storage.list_ownerless_pages()
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

    # If no pages exist yet but legacy memories do, create the page docs.
    if not updated and not ownerless:
        legacy_slugs = _legacy_page_slugs_from_memories()
        if not legacy_slugs:
            print("No ownerless pages found — nothing to do.")
            return []

        for slug in legacy_slugs:
            if page_storage.get_page(slug) is not None:
                continue
            if dry_run:
                print(f"[dry-run] Would create page '{slug}' with owner {owner_uid}")
            else:
                page_storage.create_page(
                    page_storage.Page(
                        slug=slug,
                        title=slug,
                        visibility="public",
                        owner_uids=[owner_uid],
                        description="Migrated legacy page (inferred from memories.user_id)",
                    )
                )
                page_storage.write_audit_log(
                    page_slug=slug,
                    action="page_created",
                    actor_uid=owner_uid,
                    metadata={"reason": "legacy_migration"},
                )
                print(f"Created page '{slug}' with owner {owner_uid}")
            updated.append(slug)

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
