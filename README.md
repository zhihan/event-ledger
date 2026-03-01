# Event Ledger

A family events board. Add events in plain language — an AI extracts dates, times, and locations automatically. View upcoming events on the web, grouped by "This Week" and "Upcoming."

**Homepage:** https://living-memories-488001.web.app

## Using Event Ledger

### Web App

Visit https://living-memories-488001.web.app and sign in with Google. You can create pages, add events, and invite collaborators.

### HTTP API

The API is available at `https://living-memories-488001.web.app/api`. All authenticated endpoints require a Firebase ID token in the `Authorization: Bearer <token>` header.

#### Pages

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/pages` | POST | Yes | Create a new page |
| `/pages/{slug}` | GET | No | Get page metadata |
| `/pages/{slug}` | PATCH | Yes | Rename or update a page |
| `/pages/{slug}` | DELETE | Yes | Soft-delete a page (restorable for 30 days) |
| `/pages/{slug}/restore` | POST | Yes | Restore a soft-deleted page |
| `/pages/{slug}/owners/{uid}` | DELETE | Yes | Remove a co-owner from a page |

#### Memories (events)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/pages/{slug}/memories` | POST | Yes | Add an event — pass `{"message": "..."}` in natural language |
| `/pages/{slug}/memories` | GET | No | List all events on a page |
| `/pages/{slug}/memories/{id}` | DELETE | Yes | Delete an event |

#### Invites & Users

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/pages/{slug}/invites` | POST | Yes | Create an invite link for a page |
| `/invites/{id}/accept` | POST | Yes | Accept an invite |
| `/users/me` | GET | Yes | Get current user info |
| `/users/me/pages` | GET | Yes | List pages you own |

#### Authentication

Authenticated endpoints require a Firebase ID token passed as `Authorization: Bearer <token>`. ID tokens expire after 1 hour, but you can use a long-lived **refresh token** to get fresh ones without re-authenticating.

**One-time setup (requires a browser):**

1. Sign into the web app at https://living-memories-488001.web.app
2. Open browser DevTools → Console, and run:
   ```js
   JSON.parse(Object.entries(localStorage).find(([k]) => k.startsWith('firebase:authUser:'))[1]).spiTokens.refreshToken
   ```
3. Save the returned refresh token as a secret (e.g. `FIREBASE_REFRESH_TOKEN` env var)

**Getting an ID token from the refresh token:**

```bash
curl -s -X POST \
  "https://securetoken.googleapis.com/v1/token?key=AIzaSyCRPmK9euOr_rDVcQDBh_BC9OVM2MnJF0s" \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "refresh_token", "refresh_token": "'"$FIREBASE_REFRESH_TOKEN"'"}'
# Returns JSON with "id_token" — use that as your Bearer token.
```

The refresh token does not expire unless the user's account is disabled or the token is explicitly revoked.

#### Examples

```bash
# Add an event (requires Firebase ID token)
curl -X POST https://living-memories-488001.web.app/api/pages/my-page/memories \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Team meeting next Thursday at 10am in Room A"}'

# List events on a page (no auth required)
curl https://living-memories-488001.web.app/api/pages/my-page/memories
```

---

## Development

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest              # run tests
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID |
| `LIVING_MEMORY_FIRESTORE_DATABASE` | No | Firestore database name (default: `(default)`) |

### Running the API Locally

```bash
GEMINI_API_KEY=... \
  .venv/bin/uvicorn api:app --app-dir src --reload
```

### Project Structure

- `web/` — React SPA (Firebase Auth, Firebase Hosting)
- `client/` — Legacy static HTML client (reads Firestore directly)
- `src/` — Python backend
  - `api.py` — FastAPI app (Cloud Run)
  - `committer.py` — AI-powered memory creation/deduplication
  - `memory.py` — `Memory` dataclass
  - `firestore_storage.py` — Firestore CRUD for memories
  - `page_storage.py` — Firestore CRUD for pages, invites, users
  - `publisher.py` — Static site generator
  - `cleanup.py` — Expired memory removal
  - `storage.py` — GCS attachment helpers
- `tests/` — Pytest suite (Firestore mocked)

### Deploy

- **Web App (Firebase Hosting)** — `.github/workflows/publish.yml`
- **Cloud Run API** — `./scripts/deploy_cloud_run.sh` or `.github/workflows/deploy-api.yml`

### Logging

The API emits structured logs viewable in Cloud Run's **Logs Explorer**. Each request logs `method`, `path`, `status_code`, and `duration_ms`. Cloud Trace correlation is included when the `x-cloud-trace-context` header is present.
