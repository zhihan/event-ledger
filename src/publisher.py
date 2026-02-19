"""Publisher — generates a static HTML page from memory files."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from html import escape
from pathlib import Path

from memory import Memory


def load_memories(directory: Path, today: date) -> list[Memory]:
    """Load non-expired memories from *directory*, sorted by target date."""
    memories: list[Memory] = []
    for path in sorted(directory.glob("*.md")):
        mem = Memory.load(path)
        if not mem.is_expired(today):
            memories.append(mem)
    memories.sort(key=lambda m: m.target)
    return memories


def _render_event(mem: Memory) -> str:
    """Render a single memory as an HTML list item."""
    parts = [f"<li><strong>{escape(mem.title or mem.content)}</strong>"]
    details = []
    details.append(str(mem.target))
    if mem.time:
        details.append(escape(mem.time))
    if mem.place:
        details.append(escape(mem.place))
    parts.append(f"<br>{' · '.join(details)}")
    if mem.title:
        parts.append(f"<br>{escape(mem.content)}")
    parts.append("</li>")
    return "\n".join(parts)


def generate_page(memories: list[Memory], today: date) -> str:
    """Generate a complete HTML page with this-week and future sections."""
    week_end = today + timedelta(days=(6 - today.weekday()))

    this_week = [m for m in memories if m.target <= week_end]
    future = [m for m in memories if m.target > week_end]

    def render_section(title: str, events: list[Memory]) -> str:
        if not events:
            return f"<h2>{title}</h2>\n<p>No events.</p>"
        items = "\n".join(_render_event(e) for e in events)
        return f"<h2>{title}</h2>\n<ul>\n{items}\n</ul>"

    this_week_html = render_section("This Week", this_week)
    future_html = render_section("Upcoming", future)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Living Memory</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.5rem; }}
  h2 {{ color: #555; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin-bottom: 1rem; padding: 0.75rem; background: #f8f8f8; border-radius: 6px; }}
</style>
</head>
<body>
<h1>Living Memory</h1>
{this_week_html}
{future_html}
</body>
</html>
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a static site from memories")
    parser.add_argument("--memories-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    today = date.today()
    memories = load_memories(args.memories_dir, today)
    html = generate_page(memories, today)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "index.html").write_text(html)


if __name__ == "__main__":
    main()
