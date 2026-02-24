# Event Ledger

A family events board powered by Firestore and deployed to GitHub Pages. Add events via CLI or REST API, and view them on a simple, auth-protected web page — no server-side rendering required.

**Homepage:** https://zhihan.github.io/lexington-ma-events/

## What It Does

- **Collect events** — Add memories via natural language CLI or HTTP API; an AI extracts dates, times, and locations automatically.
- **Show what's coming** — The homepage groups events into "This Week" and "Upcoming" sections, filtered in the browser.
- **Auto-expire** — Each event has an expiry date; expired events are hidden client-side and can be cleaned up with a one-liner.
- **Auth-protected** — The homepage requires Google sign-in; Firestore security rules enforce access control.

## Quick Start

### View the homepage

Visit https://zhihan.github.io/lexington-ma-events/ and sign in with Google.

### Local development (optional)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest              # run tests
```

## HTTP API

A REST API deployed to Cloud Run with Firebase Auth (ID tokens).

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/_healthz` | GET | No | Health check |
| `/pages` | POST | Firebase | Create a page |
| `/pages/{slug}` | GET | Optional | Get page metadata |
| `/pages/{slug}/memories` | POST | Firebase | Create a memory on a page |
| `/pages/{slug}/memories` | GET | Optional | List memories for a page |
| `/pages/{slug}/memories/{id}` | DELETE | Firebase | Delete a memory |
| `/pages/{slug}/invites` | POST | Firebase | Create an invite link |
| `/invites/{id}/accept` | POST | Firebase | Accept an invite |
| `/users/me` | GET | Firebase | Get current user |
| `/users/me/pages` | GET | Firebase | List pages owned by current user |

### Example

```bash
# Health check (no auth required)
curl https://YOUR-SERVICE-URL/_healthz

# Create a memory on a page (requires Firebase ID token)
curl -X POST https://YOUR-SERVICE-URL/pages/my-page/memories \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Team meeting next Thursday at 10am in Room A"}'

# List memories for a public page (no auth required)
curl https://YOUR-SERVICE-URL/pages/my-page/memories
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID |
| `LIVING_MEMORY_FIRESTORE_DATABASE` | No | Firestore database name (default: `(default)`) |

## Firebase / Client

Client uses Firebase Auth + Firestore; see `client/index.html` for config and set Firestore rules to require auth.

## Logging

The API emits structured logs viewable in Cloud Run's **Logs Explorer**. Each request logs `method`, `path`, `status_code`, and `duration_ms`. Cloud Trace correlation is included when the `x-cloud-trace-context` header is present.

## Deploy

- **GitHub Pages** — see `.github/workflows/publish.yml`
- **Cloud Run API** — `./scripts/deploy_cloud_run.sh` (or see `.github/workflows/deploy-api.yml` for CI)
