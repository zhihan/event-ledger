#!/usr/bin/env python3
"""One-time migration: import existing memories/*.md files into Firestore."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from the repo root without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from memory import Memory  # noqa: E402
import firestore_storage  # noqa: E402


def migrate(memories_dir: Path, *, dry_run: bool = False) -> int:
    """Read all markdown files and insert them into Firestore.

    Returns the number of documents created.
    """
    paths = sorted(memories_dir.glob("*.md"))
    if not paths:
        print("No memory files found.")
        return 0

    count = 0
    for path in paths:
        mem = Memory.load(path)
        if dry_run:
            print(f"[dry-run] Would import: {path.name}  (user_id={mem.user_id})")
        else:
            doc_id = firestore_storage.save_memory(mem)
            print(f"Imported {path.name} → {doc_id}")
        count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate memory markdown files into Firestore",
    )
    parser.add_argument(
        "--memories-dir", type=Path, default=Path("memories"),
        help="Directory containing *.md memory files",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be imported without writing to Firestore",
    )
    args = parser.parse_args()

    count = migrate(args.memories_dir, dry_run=args.dry_run)
    print(f"\nTotal: {count} memories {'would be ' if args.dry_run else ''}imported.")


if __name__ == "__main__":
    main()
