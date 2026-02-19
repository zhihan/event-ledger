"""Core data structures for memory entries."""

from __future__ import annotations

import frontmatter
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class Memory:
    """A single memory entry.

    Each memory has a target date (when the event occurs) and an
    expiration date (when it can safely be removed from memory).
    """

    target: date
    expires: date
    content: str
    title: str | None = None
    time: str | None = None
    place: str | None = None

    @classmethod
    def load(cls, path: Path) -> Memory:
        """Load a memory from a markdown file with YAML frontmatter."""
        post = frontmatter.load(path)
        return cls(
            target=_parse_date(post.metadata["target"]),
            expires=_parse_date(post.metadata["expires"]),
            content=post.content,
            title=post.metadata.get("title"),
            time=post.metadata.get("time"),
            place=post.metadata.get("place"),
        )

    def dump(self, path: Path) -> None:
        """Write this memory to a markdown file with YAML frontmatter."""
        metadata: dict = {
            "target": self.target.isoformat(),
            "expires": self.expires.isoformat(),
        }
        if self.title is not None:
            metadata["title"] = self.title
        if self.time is not None:
            metadata["time"] = self.time
        if self.place is not None:
            metadata["place"] = self.place
        post = frontmatter.Post(self.content, **metadata)
        path.write_text(frontmatter.dumps(post) + "\n")

    def is_expired(self, today: date | None = None) -> bool:
        """Check whether this memory has passed its expiration date."""
        if today is None:
            today = date.today()
        return today > self.expires


def _parse_date(value: str | date) -> date:
    """Parse a date from a string or pass through if already a date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
