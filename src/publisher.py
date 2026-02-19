"""Publisher — generates a static site from memory files using AI."""

from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from google import genai

from memory import Memory

SYSTEM_INSTRUCTION = (
    "You are a web designer. Given a set of memory entries and a template "
    "description, generate a single complete, self-contained HTML file. "
    "Inline all CSS. Do not use external resources. Output only the HTML, "
    "no markdown fences or commentary."
)


def load_memories(directory: Path, today: date) -> list[Memory]:
    """Load non-expired memories from *directory*, sorted by target date."""
    memories: list[Memory] = []
    for path in sorted(directory.glob("*.md")):
        mem = Memory.load(path)
        if not mem.is_expired(today):
            memories.append(mem)
    memories.sort(key=lambda m: m.target)
    return memories


def build_prompt(memories: list[Memory], template: str) -> str:
    """Format memories and template into a prompt for the AI."""
    parts = [f"Template:\n{template}\n", "Memories:"]
    for mem in memories:
        header = f"- [{mem.target}]"
        if mem.title:
            header += f" {mem.title}"
        parts.append(f"{header}\n{mem.content}")
    return "\n\n".join(parts)


def generate_site(prompt: str) -> str:
    """Call Gemini to produce an HTML page from the prompt."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )
    return response.text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a static site from memories")
    parser.add_argument("--memories-dir", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    today = date.today()
    memories = load_memories(args.memories_dir, today)
    template_text = args.template.read_text()
    prompt = build_prompt(memories, template_text)
    html = generate_site(prompt)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "index.html").write_text(html)


if __name__ == "__main__":
    main()
