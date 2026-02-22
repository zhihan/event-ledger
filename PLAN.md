# Multi-User Living Memory — Evolution Plan

Steps 1 (user_id) and 2 (Firestore) are complete. Steps 3–4 remain.

---

## Step 2: Migrate Storage from Git to Cloud Firestore

**Goal:** Replace markdown-file-on-disk storage with Firestore documents. Enables multi-user access without git conflicts.

### Why Firestore
- Document-oriented: Memory dataclass maps naturally to a Firestore document
- Server-side queries: filter by `user_id`, query by `target` date range, filter expired
- Serverless with generous free tier
- Already in GCP ecosystem (attachments already use GCS)

### Data Model
```
Collection: memories
Document ID: auto-generated
Fields:
  user_id: string
  target: timestamp | null
  expires: timestamp
  title: string | null
  time: string | null
  place: string | null
  content: string
  attachments: array<string> | null
  created_at: timestamp
  updated_at: timestamp
```

### Changes

- **New `src/firestore_storage.py`** — CRUD operations:
  - `save_memory(memory)` → creates/updates a Firestore document
  - `load_memories(user_id)` → queries by user_id, excludes expired
  - `load_all_memories()` → for admin/migration use
  - `delete_memory(doc_id)` → deletes a document
- **`src/memory.py`** — Add `to_dict()` / `from_dict()` methods for Firestore serialization. Keep `load()`/`dump()` for backward compatibility during migration.
- **`src/committer.py`** — Replace file-based `load_memories()` and `dump()` with Firestore calls. Remove git commit/push logic.
- **`src/cleanup.py`** — Replace file-based cleanup with Firestore query for expired docs + delete.
- **Migration script** — One-time script to read all `memories/*.md` files and insert them into Firestore.
- **`src/publisher.py`** — Update to read from Firestore (or deprecate if client-side API is ready).

### Verification
- Migration script moves all existing memories to Firestore
- Committer creates memories in Firestore
- Cleanup deletes expired Firestore documents
- `pytest` passes with Firestore mocked in tests

---

## Step 3: Expose the Committer as a Public API

**Goal:** Turn the committer from a CLI into an HTTP API on Google Cloud Run.

### API Design
```
POST /memories
  Headers: Authorization: Bearer <token>
  Body: { "message": "Team meeting Thursday 10am Room A", "attachments": [...] }
  → AI processes message, creates/updates memory
  Response: { "id": "...", "action": "created", "memory": {...} }

GET /memories
  Headers: Authorization: Bearer <token>
  Query: ?user_id=alice
  → Returns user's non-expired memories
  Response: { "memories": [...] }

DELETE /memories/:id
  Headers: Authorization: Bearer <token>
  → Deletes a memory
```

### Auth
- Firebase Authentication or API keys — TBD based on OpenClaw integration needs
- User ID derived from authenticated token

### Changes
- **New `src/api.py`** — Flask/FastAPI HTTP server wrapping committer logic
- **`Dockerfile`** — Container for Cloud Run deployment
- **`src/committer.py`** — Refactor core logic into reusable functions (separate from CLI arg parsing)
- **CI/CD** — GitHub Actions workflow to build and deploy to Cloud Run on push

### Verification
- `curl POST /memories` creates a memory in Firestore
- `curl GET /memories?user_id=alice` returns only Alice's memories
- Deployed on Cloud Run and accessible via HTTPS

---

## Step 4: Package as an OpenClaw Skill

**Goal:** Make the committer accessible as an [OpenClaw](https://openclaw.ai/) skill.

### Changes
- **New `openclaw/SKILL.md`** — Skill definition file describing:
  - What the skill does (memorize events, retrieve upcoming events)
  - When to activate (user mentions remembering, scheduling, events)
  - How it calls the Living Memory HTTP API (Step 3)
- Auth: API key stored in OpenClaw's secrets/config

### Verification
- Skill is installable via OpenClaw
- "Remember team meeting Thursday 10am" triggers the skill and creates a memory
- "What's coming up this week?" retrieves and displays memories

---

## Implementation Order

Each step builds on the previous:

1. ~~**Step 1 (user_id)**~~ — Done
2. ~~**Step 2 (Firestore)**~~ — Done (branch `step2-firestore`)
3. **Step 3 (API)** — Requires Step 2. Wraps the Firestore-backed committer in HTTP.
4. **Step 4 (OpenClaw)** — Requires Step 3. Thin integration layer on top of the API.
