# Event Ledger

Event Ledger is a Firebase- and Firestore-backed scheduling app with two active product layers in the same repository:

- `v1` legacy pages and memories: AI-assisted event capture on shared pages
- `v2` workspaces, recurring series, occurrences, check-ins, notifications, and assistant actions

The current web app is deployed at `https://living-memories-488001.web.app`.

## Current Architecture

### Backend

- `src/api.py` exposes the legacy page and memory API.
- `src/api_v2.py` exposes the newer workspace, series, occurrence, check-in, notification, cohort, ICS, and assistant APIs.
- Firestore is the primary datastore for both models.
- Firebase Auth provides user authentication for authenticated routes.
- Gemini is used for natural-language parsing in the legacy committer flow and for the organizer assistant.

### Frontend

- `web/` is the primary React SPA.
- `client/admin.html` is a legacy admin page kept for compatibility.
- The React app already routes primarily around workspaces and recurring schedules, while still retaining legacy page routes.

### Domain Models

Legacy domain:

- `Page`
- `Memory`

Current pivot domain:

- `Workspace`
- `Series`
- `Occurrence`
- `CheckIn`
- `NotificationRule`
- `DeliveryLog`
- study/cohort records

## Main User Flows

### Legacy page and memory flow

1. Create a page.
2. Send natural language to `POST /pages/{slug}/memories`.
3. The committer extracts structured memory entries with Gemini.
4. The API stores resulting `Memory` documents in Firestore.

### Workspace and recurrence flow

1. Create a workspace.
2. Create one or more recurring series in that workspace.
3. Generate occurrences for a date window.
4. Edit, reschedule, complete, or cancel individual occurrences.
5. Record participant check-ins and configure notification rules.

### Organizer assistant flow

1. Send a message to the assistant endpoint for a workspace.
2. The assistant proposes a structured action.
3. The proposed action is stored as a pending action.
4. The user confirms or cancels it.
5. Confirmation executes the action against the workspace data.

## Local Development

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Python tests

```bash
.venv/bin/pytest
```

Run a single test:

```bash
.venv/bin/pytest tests/test_api_v2.py::TestSeriesEndpoints::test_create_series
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Required for AI-backed flows | Gemini API key |
| `GOOGLE_CLOUD_PROJECT` | Usually required outside tests | GCP project ID |
| `LIVING_MEMORY_FIRESTORE_DATABASE` | Optional | Firestore database name |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram webhook and bot integration |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Optional | Email notification delivery |
| `FROM_EMAIL` | Optional | Sender address for email notifications |
| `APP_BASE_URL` | Optional | Base URL used in links and ICS output |

### Run the API locally

```bash
GEMINI_API_KEY=... \
  .venv/bin/uvicorn api:app --app-dir src --reload
```

The app accepts both direct paths like `/pages/...` and Firebase Hosting rewritten paths like `/api/pages/...`.

### Run the React app locally

```bash
cd web
npm install
npm run dev
```

## Useful Commands

### Login CLI

```bash
login
login whoami
login token
login logout
```

### Committer

```bash
GEMINI_API_KEY=... .venv/bin/python -m committer \
  --message "Team meeting next Thursday at 10am in Room A"
```

### Cleanup

```bash
.venv/bin/python -m cleanup
```

### Publisher

The static publisher is still present for the legacy memory model:

```bash
.venv/bin/python -m publisher --output-dir site/
```

## API Overview

Authenticated routes require a Firebase ID token in `Authorization: Bearer <token>`.

### Legacy API groups

- `/users/me`
- `/users/me/pages`
- `/pages`
- `/pages/{slug}`
- `/pages/{slug}/invites`
- `/invites/{id}/accept`
- `/pages/{slug}/memories`
- `/pages/{slug}/memories/stream`

### V2 API groups

- `/v2/workspaces`
- `/v2/workspaces/{workspace_id}/members`
- `/v2/workspaces/{workspace_id}/series`
- `/v2/workspaces/{workspace_id}/occurrences`
- `/v2/series/{series_id}`
- `/v2/series/{series_id}/occurrences`
- `/v2/occurrences/{occurrence_id}`
- `/v2/occurrences/{occurrence_id}/check-ins`
- `/v2/workspaces/{workspace_id}/notification-rules`
- `/v2/workspaces/{workspace_id}/cohorts`
- `/v2/workspaces/{workspace_id}/assistant`
- `/v2/assistant/actions/{action_id}/confirm`
- `/v2/assistant/actions/{action_id}/cancel`

### Example: create a legacy memory

```bash
curl -X POST https://living-memories-488001.web.app/api/pages/my-page/memories \
  -H "Authorization: Bearer $(login token)" \
  -H "Content-Type: application/json" \
  -d '{"message": "Team meeting next Thursday at 10am in Room A"}'
```

### Example: create a workspace

```bash
curl -X POST https://living-memories-488001.web.app/v2/workspaces \
  -H "Authorization: Bearer $(login token)" \
  -H "Content-Type: application/json" \
  -d '{"title": "Weekly Standup", "type": "shared", "timezone": "America/New_York"}'
```

## Repository Layout

- `src/` Python backend
- `web/` React SPA
- `client/` legacy static admin UI
- `tests/` pytest suite
- `docs/design/` retained product and design docs for the workspace/series pivot
- `scripts/` operational and migration scripts

## Notes on Repository State

This repo is in an intentional transition state. The legacy page/memory stack is still implemented and tested, while the newer workspace/series stack is the active direction of the product and frontend. Documentation in this repository is aligned to that hybrid reality rather than pretending the migration is still only planned.
