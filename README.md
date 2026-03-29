# Event Ledger

Event Ledger is a Firebase- and Firestore-backed recurring-schedule platform with workspaces, series, occurrences, check-ins, notifications, and an organizer assistant.

The current web app is deployed at `https://living-memories-488001.web.app`.

## Architecture

### Backend

- `src/api.py` is the main FastAPI entry point (health check, middleware, mounts the v2 router).
- `src/api_v2.py` exposes the workspace, series, occurrence, check-in, notification, cohort, ICS, Telegram webhook, and assistant APIs.
- `src/db.py` provides the shared Firestore client factory.
- Firestore is the primary datastore.
- Firebase Auth provides user authentication for authenticated routes.
- Gemini powers the organizer assistant.

### Frontend

- `web/` is the primary React SPA, organized around workspaces and recurring schedules.

### Domain Models

- `Workspace`
- `Series`
- `Occurrence`
- `CheckIn`
- `NotificationRule`
- `DeliveryLog`
- Study/cohort records

## Main User Flows

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

## API Overview

Authenticated routes require a Firebase ID token in `Authorization: Bearer <token>`.

### API groups

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
- `tests/` pytest suite
- `docs/design/` product and design docs for the workspace/series platform
- `scripts/` operational scripts
