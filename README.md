# Living Memory

A static website generator with no database. The "database" is an organized collection of markdown files stored in a git repo.

## How It Works

1. **Committer** — CLI tool that adds event memories to the repo and pushes to GitHub.
2. **Publisher** — GitHub Actions workflow that generates a static HTML page and deploys to GitHub Pages.

```
User → committer → git push → GitHub Actions → publisher → static site
```

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Add a memory

Requires `GEMINI_API_KEY`. Set it in a `.env` file at the project root or as an environment variable.

```bash
.venv/bin/python -m committer --message "Team meeting next Thursday at 10am in Room A"
```

Options:
- `--attach <file>` — attach a file (uploaded to cloud storage); repeatable for multiple files
- `--memories-dir` — directory for memory files (default: `memories/`)
- `--no-push` — skip git push
- `--today 2026-02-18` — override today's date (for testing)

The AI extracts event details from your message and decides whether to create a new memory or update an existing one.

### Generate the site locally

```bash
python -m publisher --memories-dir memories/ --output-dir site/
```

The output is a single `index.html` with two sections: **This Week** and **Upcoming**.

## Memory Format

Each memory is a markdown file with YAML frontmatter:

```markdown
---
target: 2026-03-01
expires: 2026-04-01
title: Team Meeting
time: "10:00"
place: Room A
---
Weekly planning session.
```

Required fields: `target`, `expires`. Optional: `title`, `time`, `place`.

## Firestore Storage (optional)

Instead of git/markdown files, memories can be stored in Google Cloud Firestore. Enable it with `--firestore` or by setting `LIVING_MEMORY_STORAGE=firestore`.

### Setup

1. **GCP project** — create a Firestore database in Native mode.
2. **Authentication** — set `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON key, or run on GCE/Cloud Run where default credentials are available.
3. **Database ID** — if your Firestore database is not `(default)`, set the database name:
   ```bash
   export LIVING_MEMORY_FIRESTORE_DATABASE=living-memories-db
   ```
   You can also set `GOOGLE_CLOUD_PROJECT` if the project cannot be inferred from credentials.
4. **Emulator (local dev)** — use the [Firestore Emulator](https://cloud.google.com/firestore/docs/emulator):
   ```bash
   gcloud emulators firestore start
   export FIRESTORE_EMULATOR_HOST="localhost:8080"
   ```

### Usage with Firestore

```bash
# Add a memory via Firestore
.venv/bin/python -m committer --message "Team meeting Thursday 10am" --firestore

# Generate site from Firestore
.venv/bin/python -m publisher --output-dir site/ --firestore

# Clean up expired memories
.venv/bin/python -m cleanup --firestore

# Or set the env var globally
export LIVING_MEMORY_STORAGE=firestore
```

### Migration

Import existing markdown files into Firestore:

```bash
python scripts/migrate_to_firestore.py --memories-dir memories/
# Use --dry-run to preview without writing
```

## Client-Side Page (Step 1.5)

A fully static HTML page that reads memories directly from Firestore in the browser. No server needed — suitable for GitHub Pages or any static host.

### How it works

`client/index.html` uses the Firebase Web SDK to query the `memories` collection in Firestore, filters out expired memories client-side, and renders **This Week** / **Upcoming** sections matching the server-side publisher output.

### Usage

1. Open `client/index.html` in a browser (or deploy to GitHub Pages).
2. By default it shows events for `user_id=cambridge-lexington`.
3. Override via query parameter: `?user_id=other-group`.

### Firebase config

The following values are embedded in `client/index.html`:

| Key | Value |
|-----|-------|
| `projectId` | `living-memories-488001` |
| `databaseId` | `living-memories-db` |
| `collection` | `memories` |
| `apiKey` | `AIzaSyCbx3sME8MqAqn35tweXfpLfjnpirBjFZY` |

The API key is safe to embed publicly — it only identifies the project. Access control is enforced by Firestore security rules.

### Firestore security rules (private via Google sign-in)

To make the GitHub Pages client app private, require Firebase Authentication for reads and deny all writes:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /memories/{docId} {
      allow read: if request.auth != null;
      allow write: if false;
    }
  }
}
```

**Important:** In Firebase Console → Authentication → Settings → Authorized domains, add:
- `zhihan.github.io`

The API key is not a secret; access control is enforced by Firestore security rules.

### Named database support

The Firebase Web SDK (v10.4+) supports non-default database IDs via `getFirestore(app, "database-id")`. The client page targets the `living-memories-db` database directly. If you encounter issues with named database access, you can either:
- Migrate data to the `(default)` database, or
- Update `DATABASE_ID` in `client/index.html` to `"(default)"`.

## Running Tests

```bash
.venv/bin/pytest
```
