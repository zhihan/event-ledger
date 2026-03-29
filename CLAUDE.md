# CLAUDE.md

This file gives repo-specific guidance for coding agents working in this repository.

## Project Overview

Event Ledger is no longer just a page-based family events board. The repository currently contains two active layers:

- legacy `Page` and `Memory` flows for AI-assisted event capture
- newer `Workspace`, `Series`, `Occurrence`, `CheckIn`, notification, study, and assistant flows for a recurring-schedule platform

Do not assume the repo is fully migrated to the newer model, and do not assume the older page/memory model is dead. Both are present in production code, tests, and frontend routes.

## Primary Runtime Surfaces

- `src/api.py`
  Legacy FastAPI surface for pages, memories, invites, and users.
- `src/api_v2.py`
  Newer FastAPI surface for workspaces, membership, recurring series, occurrences, check-ins, notifications, cohorts, ICS export, Telegram webhook handling, and assistant actions.
- `web/`
  Primary React SPA. It already favors workspace-centric routes but still keeps legacy page routes.
- `client/admin.html`
  Legacy admin UI retained for compatibility and manual operations.

## Core Backend Modules

- `src/models.py`
  Canonical dataclasses for `Workspace`, `Series`, `Occurrence`, `CheckIn`, `NotificationRule`, and `DeliveryLog`.
- `src/recurrence.py`
  Pure recurrence engine for generating UTC occurrence timestamps from schedule rules.
- `src/occurrence_service.py`
  Service layer bridging recurrence generation with Firestore persistence.
- `src/assistant.py`
  Organizer assistant orchestration.
- `src/assistant_actions.py`
  Pending-action storage plus confirm/cancel/execute flow.
- `src/committer.py`
  Legacy Gemini-backed natural-language to `Memory` extraction flow.

## Storage Modules

- `src/firestore_storage.py`
  Legacy memory storage.
- `src/page_storage.py`
  Legacy page, invite, user, and audit-log storage.
- `src/workspace_storage.py`
  Workspace and membership storage.
- `src/series_storage.py`
  Series, occurrence, check-in, notification rule, and delivery log storage.
- `src/study_storage.py`
  Cohort, badge, and streak snapshot storage.

## Product Reality

When documenting or changing behavior, reflect the current hybrid state:

- `v1` page/memory flows still exist and are tested.
- `v2` workspace/series flows are the active product direction.
- The React app already exposes workspace-first navigation.
- Some integrations are intentionally incomplete or stubbed, especially external channels and some notification paths.

## Development

Setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Run all tests:

```bash
.venv/bin/pytest
```

Run the API locally:

```bash
GEMINI_API_KEY=... \
  .venv/bin/uvicorn api:app --app-dir src --reload
```

Run the React app:

```bash
cd web
npm install
npm run dev
```

## Authentication

Authenticated API routes use Firebase ID tokens. For local manual testing, use:

```bash
login
login token
login whoami
login logout
```

## Documentation Guidance

Prefer keeping these docs aligned with the actual code instead of historical plans:

- `README.md` should describe the repository as it exists now.
- Historical issue plans that no longer match the code should be removed rather than left as if they were current.
- Product-level docs under `docs/design/` may remain if they still describe the active direction of the project.
