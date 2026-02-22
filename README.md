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

A REST API deployed to Cloud Run with static API key auth. The API key is a secret — do not expose it in client code.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/_healthz` | GET | No | Health check |
| `/memories` | POST | Yes | Create a memory |
| `/memories` | GET | Yes | List memories |
| `/memories/{id}` | DELETE | Yes | Delete a memory |

### Example

```bash
# Health check (no auth required)
curl https://YOUR-SERVICE-URL/_healthz

# Create a memory
curl -X POST https://YOUR-SERVICE-URL/memories \
  -H "Authorization: Bearer $EVENT_LEDGER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Team meeting next Thursday at 10am in Room A"}'

# List memories
curl https://YOUR-SERVICE-URL/memories \
  -H "Authorization: Bearer $EVENT_LEDGER_API_KEY"

# Delete a memory
curl -X DELETE https://YOUR-SERVICE-URL/memories/DOCUMENT_ID \
  -H "Authorization: Bearer $EVENT_LEDGER_API_KEY"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `EVENT_LEDGER_API_KEY` | Yes (API only) | Bearer token for API auth — keep secret |
| `GOOGLE_CLOUD_PROJECT` | Yes (API only) | GCP project ID |
| `LIVING_MEMORY_FIRESTORE_DATABASE` | No | Firestore database name (default: `(default)`) |

## Firebase / Client

Client uses Firebase Auth + Firestore; see `client/index.html` for config and set Firestore rules to require auth.

## Deploy

- **GitHub Pages** — see `.github/workflows/publish.yml`
- **Cloud Run API** — see `.github/workflows/deploy-api.yml`
