# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Living Memory is a static website generator similar to a CMS, but with no database. The "database" is an organized structure of markdown files and other raw files stored in a git repo (the "memory").

## Architecture

The system has two independent components that do not necessarily run on the same machine:

- **Committer** — A conversational agent that chats with the user. When the user asks it to memorize something, it examines the existing memory, deduplicates, updates the memory with the new information, commits the change, and pushes to GitHub.
- **Publisher** — Responds to GitHub pushes. It reads the latest memory, generates a static website from it using a template, and deploys to a hosting service.

The flow: User → Committer → git push → Publisher → static site deployment.

## Memory Format

Each memory is a markdown file with YAML frontmatter. Required fields:
- `target` — date the event occurs (ISO 8601)
- `expires` — date when the memory can safely be removed

The core data structure is `Memory` in `src/memory.py`.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Run all tests:
```bash
.venv/bin/pytest
```

Run a single test:
```bash
.venv/bin/pytest tests/test_memory.py::test_name
```

## Publisher

Generate a static site locally:
```bash
GEMINI_API_KEY=your-key .venv/bin/python -m publisher \
  --memories-dir memories/ \
  --template templates/blog.md \
  --output-dir site/
```

In CI, the publisher runs automatically via `.github/workflows/publish.yml` on pushes that change `memories/` or `templates/`.

## Repository Structure

- `src/` - Python source code
  - `memory.py` — core Memory dataclass with load/dump/expiry
  - `publisher.py` — static site generator (load memories → AI prompt → HTML)
- `memories/` - Memory markdown files (the "database")
- `templates/` - Markdown template definitions for site layout (blog, portfolio, wiki)
- `tests/` - Pytest test suite
- `.github/workflows/` - CI/CD (publish on push)
