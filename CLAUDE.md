# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Event Ledger is a static website generator similar to a CMS. It supports two storage backends: **file-based** (markdown files in a git repo) and **Firestore** (Google Cloud Firestore documents). The file-based backend is the default; Firestore can be enabled via the `--firestore` CLI flag or by setting `LIVING_MEMORY_STORAGE=firestore`.

## Architecture

The system has two independent components that do not necessarily run on the same machine:

- **Committer** — A conversational agent that chats with the user. When the user asks it to memorize something, it examines the existing memory, deduplicates, updates the memory with the new information, commits the change, and pushes to GitHub. The core logic is exposed as `commit_memory_firestore()` for programmatic use by the API.
- **HTTP API** — A FastAPI app (`src/api.py`) deployed to Cloud Run. Provides REST endpoints for creating, listing, and deleting memories via Firestore. Uses static API key auth (`EVENT_LEDGER_API_KEY`).
- **Publisher** — Responds to GitHub pushes. It reads the latest memory, generates a static HTML page with two sections (this week's events and upcoming events), and deploys to GitHub Pages.

The flow: User → Committer/API → Firestore ← client/index.html (GitHub Pages).

**Future:** The memory files (`memories/`) will be separated into their own repository. For now they live alongside the publisher code.

## Memory Format

Each memory is a markdown file with YAML frontmatter. Required fields:
- `target` — date the event occurs (ISO 8601)
- `expires` — date when the memory can safely be removed

Optional fields:
- `title` — short event name
- `time` — time of day (free-form string, e.g. "10:00")
- `place` — location of the event

The core data structure is `Memory` in `src/memory.py`. It supports `to_dict()`/`from_dict()` for Firestore serialization and `load()`/`dump()` for file-based storage.

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

## Committer

Add or update a memory using natural language (requires `GEMINI_API_KEY` env var):
```bash
GEMINI_API_KEY=... .venv/bin/python -m committer \
  --memories-dir memories/ \
  --message "Team meeting next Thursday at 10am in Room A"
```

Use `--no-push` to skip `git push` (useful for local testing).
Use `--today 2026-02-18` to override today's date (useful for testing).

The AI reads existing memories and decides whether to create a new one or update an existing one.

### Firestore mode

```bash
GEMINI_API_KEY=... .venv/bin/python -m committer \
  --firestore \
  --message "Team meeting next Thursday at 10am in Room A"
```

Or set the environment variable `LIVING_MEMORY_STORAGE=firestore` to use Firestore by default (applies to committer, publisher, and cleanup).

## Publisher

Generate a static site locally:
```bash
.venv/bin/python -m publisher --memories-dir memories/ --output-dir site/
```

In CI, the publisher runs automatically via `.github/workflows/publish.yml` on pushes that change `memories/`.

## Cleanup

Remove expired memories (file-based):
```bash
.venv/bin/python -m cleanup --memories-dir memories/
```

Remove expired memories (Firestore):
```bash
.venv/bin/python -m cleanup --firestore
```

## Migration (files → Firestore)

One-time migration of existing `memories/*.md` files into Firestore:
```bash
python scripts/migrate_to_firestore.py --memories-dir memories/
```

Use `--dry-run` to preview without writing to Firestore.

## HTTP API

Run locally:
```bash
EVENT_LEDGER_API_KEY=dev-key GEMINI_API_KEY=... \
  .venv/bin/uvicorn api:app --app-dir src --reload
```

Endpoints: `GET /healthz`, `POST /memories`, `GET /memories`, `DELETE /memories/{id}`. All except `/healthz` require `Authorization: Bearer <key>`. Deployed to Cloud Run via `.github/workflows/deploy-api.yml`.

## Client-Side Page

A static HTML page (`client/index.html`) that reads Firestore directly in the browser using the Firebase Web SDK. No server required — deploy to GitHub Pages or open locally. Supports `?user_id=...` query parameter (default: `cambridge-lexington`).

## Repository Structure

- `client/` - Client-side Firestore reader (static HTML/JS)
- `src/` - Python source code
  - `memory.py` — core Memory dataclass with load/dump/to_dict/from_dict/expiry
  - `firestore_storage.py` — Firestore CRUD: save, load, delete, find_by_title, delete_expired
  - `committer.py` — CLI + core `commit_memory_firestore()` function for adding/updating memories
  - `api.py` — FastAPI HTTP API for Cloud Run (REST endpoints for memories)
  - `cleanup.py` — delete expired memories and purge GCS attachments (file-based or Firestore)
  - `publisher.py` — static site generator (load memories → HTML with this-week/upcoming sections)
  - `storage.py` — GCS upload/delete helpers for file attachments
- `memories/` - Memory markdown files (file-based backend)
- `scripts/` - One-time scripts (e.g. `migrate_to_firestore.py`)
- `templates/` - HTML template for site layout
- `tests/` - Pytest test suite (Firestore mocked in tests)
- `Dockerfile` - Container image for Cloud Run API deployment
- `.github/workflows/` - CI/CD (publish on push, deploy API to Cloud Run)
