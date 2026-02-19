"""Committer — accepts event details and writes memory files to git."""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

from memory import Memory


def slugify(title: str | None, target: date) -> str:
    """Generate a filename from the title and target date."""
    prefix = target.isoformat()
    if not title:
        return f"{prefix}.md"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{prefix}-{slug}.md"


def find_duplicate(memories_dir: Path, target: date, title: str | None) -> Path | None:
    """Find an existing memory with the same target date and title."""
    for path in memories_dir.glob("*.md"):
        mem = Memory.load(path)
        if mem.target == target and mem.title == title:
            return path
    return None


def commit_memory(
    memories_dir: Path,
    target: date,
    expires: date,
    content: str,
    title: str | None = None,
    time: str | None = None,
    place: str | None = None,
) -> Path:
    """Write a memory file, deduplicating against existing memories."""
    existing = find_duplicate(memories_dir, target, title)
    if existing:
        path = existing
    else:
        path = memories_dir / slugify(title, target)

    mem = Memory(
        target=target,
        expires=expires,
        content=content,
        title=title,
        time=time,
        place=place,
    )
    mem.dump(path)
    return path


def git_commit_and_push(path: Path, push: bool = True) -> None:
    """Stage, commit, and optionally push the memory file."""
    subprocess.run(["git", "add", str(path)], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Update memory: {path.name}"],
        check=True,
    )
    if push:
        subprocess.run(["git", "push"], check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Commit a memory to the repository")
    parser.add_argument("--memories-dir", type=Path, required=True)
    parser.add_argument("--target", type=date.fromisoformat, required=True)
    parser.add_argument("--expires", type=date.fromisoformat, required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--title")
    parser.add_argument("--time")
    parser.add_argument("--place")
    parser.add_argument("--no-push", action="store_true", help="Skip git push")
    args = parser.parse_args(argv)

    path = commit_memory(
        memories_dir=args.memories_dir,
        target=args.target,
        expires=args.expires,
        content=args.content,
        title=args.title,
        time=args.time,
        place=args.place,
    )
    git_commit_and_push(path, push=not args.no_push)


if __name__ == "__main__":
    main()
