# Design Doc — Issue #34: Implement Users and Pages

## 0) Context / Problem Statement
Issue #34 proposes evolving the “living memory” app toward a **social-app-like model**:
- Every logged-in person is a distinct **User**.
- Users can create **Pages**.
- A Page can have **one or more owners** (must have at least one).
- **All Pages are public**.
- **Personal pages are private**.
- This implies moving from a “single-family board / single-tenant ledger” vibe into a more general **web app** with first-class identity + authorization.

This repo already has:
- Firestore-backed `memories` documents with `user_id`
- a `client/` using Firebase Auth + Firestore
- a Cloud Run REST API (currently API-key protected)

The missing piece is a coherent **multi-user + multi-page** authorization and data model.

---

## 1) Goals

### Functional
1. **User identity**: Each Firebase Auth user is a first-class user (by UID).
2. **Pages**:
   - Users can create pages.
   - Pages have **≥ 1 owner**.
   - Pages can be **co-owned** by multiple users.
3. **Visibility**:
   - **Public pages**: readable by anyone (including logged-out users).
   - **Personal pages**: private; readable only by the owners (and optionally members, if we add membership).
4. **Memories belong to pages**: a memory is associated with a page (not directly with a user).
5. **Web app architecture alignment**:
   - Client can route to `/p/{slug}` or similar.
   - API supports page-scoped memory CRUD.

### Non-goals (for this issue)
- “Following”, likes, comments, notifications.
- Fine-grained roles beyond **owner** (e.g., editor/viewer), unless needed for future extension.
- Paid plans / billing.
- Cross-page search / discovery.

---

## 2) Terminology
- **User**: Firebase Auth identity (UID). Stored as `users/{uid}` for profile + metadata.
- **Page**: A container for memories. Has owners and a visibility mode.
- **Personal Page**: A page intended to be private, typically 1:1 with a user (one owner = user).
- **Public Page**: A page visible to all users (and optionally anonymous visitors).
- **Owner**: A user who can manage a page and write/delete its memories.

Optional future term:
- **Member**: a user with access but not owner privileges.

---

## 3) Current State (as of PLAN.md / README.md)
- Firestore collection `memories` exists and stores `user_id: string`.
- API endpoints exist for `/memories` (POST/GET/DELETE) protected by a static bearer token `EVENT_LEDGER_API_KEY`.
- `client/` uses Firebase Auth + Firestore to display memories.

Gaps relative to Issue #34:
- No `pages` collection.
- No ownership model.
- No public vs personal/private visibility concept.
- No clear relationship between “user” and “their memories” beyond a string field.

---

## 4) Proposed Data Model

### 4.1 Collections overview
```
users/{uid}
pages/{pageId}
pages/{pageId}/invites/{inviteId}        (optional, if we implement invites)
memories/{memoryId}
```

### 4.2 `users/{uid}`
**Purpose:** profile + bookkeeping.

Fields:
- `uid: string` (redundant but convenient)
- `created_at: timestamp`
- `display_name: string | null`
- `photo_url: string | null`
- `default_personal_page_id: string | null`

Notes:
- The source of truth for identity is Firebase Auth; this document is for app metadata.

### 4.3 `pages/{pageId}`
**Purpose:** shared container and authorization boundary.

Fields:
- `page_id: string` (redundant)
- `slug: string` (unique, URL-friendly)
- `title: string`
- `description: string | null`
- `visibility: "public" | "personal"`
  - `public`: readable by anyone
  - `personal`: private
- `owner_uids: array<string>` (must be non-empty)
- `created_at: timestamp`
- `updated_at: timestamp`

Constraints:
- `owner_uids.length >= 1`
- `slug` unique across all pages

### 4.4 `memories/{memoryId}` (updated)
**Key change:** associate memories with pages.

Fields (existing + new):
- `page_id: string`  ✅ new (required)
- `user_id: string`  ⚠️ legacy (keep temporarily for migration/back-compat)
- `target: timestamp | null`
- `expires: timestamp`
- `title: string | null`
- `time: string | null`
- `place: string | null`
- `content: string`
- `attachments: array<string> | null`
- `created_at: timestamp`
- `updated_at: timestamp`

Rule:
- A memory’s access is determined by its parent page’s visibility + ownership.

---

## 5) Firestore Indexes

### 5.1 Required queries
- List memories for a page (exclude expired, sort by target):
  - `where page_id == X AND expires > now` (or `expires >= now`)
  - order by `target` (or `created_at`) depending on UI

Suggested composite indexes:
1. `memories`: `(page_id ASC, expires ASC)`
2. `memories`: `(page_id ASC, target ASC)`
3. If you filter on non-expired and order by target, you may need:
   - `(page_id ASC, expires ASC, target ASC)` (depending on query shape)

### 5.2 Slug lookup
- `pages` by slug:
  - option A: make `pageId == slug` (simplest, no index)
  - option B: keep `slug` field and query `where slug == "foo"` (needs index)

Recommendation: **Use slug as document id** if feasible.
- Pros: simplest routing and rules checks.
- Cons: renaming slug becomes a document move.

---

## 6) Authorization Model

### 6.1 High-level rules
- **Public page**: anyone can read.
- **Personal page**: only owners can read.
- Writes (create/update/delete memories): owners only.

### 6.2 Firestore Security Rules (sketch)
Pseudocode (not exact syntax):

```
function isSignedIn() { return request.auth != null; }
function uid() { return request.auth.uid; }
function page(pageId) { return get(/databases/$(database)/documents/pages/$(pageId)).data; }
function isOwner(pageId) { return isSignedIn() && (uid() in page(pageId).owner_uids); }
function canReadPage(pageId) {
  let p = page(pageId);
  return p.visibility == "public" || isOwner(pageId);
}

match /pages/{pageId} {
  allow read: if resource.data.visibility == "public" || isOwner(pageId);
  allow create: if isSignedIn() && request.resource.data.owner_uids.size() >= 1
                && (uid() in request.resource.data.owner_uids);
  allow update, delete: if isOwner(pageId);
}

match /memories/{memoryId} {
  allow read: if canReadPage(resource.data.page_id);
  allow create: if isOwner(request.resource.data.page_id);
  allow update, delete: if isOwner(resource.data.page_id);
}

match /users/{userId} {
  allow read: if isSignedIn() && uid() == userId;
  allow write: if isSignedIn() && uid() == userId;
}
```

Important implementation notes:
- If we keep legacy `user_id`, security must be page-based only; otherwise we get inconsistent enforcement.
- Consider preventing owners array from being emptied on update.

---

## 7) API Changes (Cloud Run)

### 7.1 Auth
Move from static API key to **Firebase ID token** verification.
- Client sends `Authorization: Bearer <firebase_id_token>`
- API verifies token via Firebase Admin SDK, obtains `uid`.

(We can keep API-key mode temporarily during migration/rollout.)

### 7.2 Endpoints
Suggested resource-oriented endpoints:

#### Users
- `GET /users/me`
  - returns uid + default personal page

#### Pages
- `POST /pages`
  - create page
- `GET /pages/{slug}`
  - fetch page metadata (public data if visibility public)
- `POST /pages/{slug}/owners`
  - add co-owner (requires owner)
- `DELETE /pages/{slug}/owners/{uid}`
  - remove co-owner (requires owner; must keep ≥1 owner)

#### Memories (page-scoped)
- `POST /pages/{slug}/memories`
- `GET /pages/{slug}/memories`
- `DELETE /pages/{slug}/memories/{id}`

### 7.3 Request/Response examples
Create page:
```json
POST /pages
Authorization: Bearer <id_token>
{
  "slug": "lexington-family",
  "title": "Lexington Family",
  "visibility": "public"
}

200
{
  "page": {
    "page_id": "lexington-family",
    "slug": "lexington-family",
    "title": "Lexington Family",
    "visibility": "public",
    "owner_uids": ["abc123"],
    "created_at": "..."
  }
}
```

Create memory on a page:
```json
POST /pages/lexington-family/memories
Authorization: Bearer <id_token>
{
  "message": "Team meeting next Thursday at 10am in Room A",
  "attachments": []
}

200
{
  "action": "created",
  "memory": {
    "id": "...",
    "page_id": "lexington-family",
    "content": "...",
    "target": "...",
    "expires": "..."
  }
}
```

---

## 8) Client UX / Routes

### 8.1 Routes
- `/` — landing
- `/sign-in` — Google sign-in
- `/me` — redirects to personal page
- `/p/{slug}` — page view
- `/p/{slug}/settings` — owners, visibility

### 8.2 Flows
**First-time sign-in**:
1. User signs in with Google.
2. Client calls `GET /users/me`.
3. If no personal page exists, create one:
   - slug: derived from uid or username-like slug
   - visibility: `personal`
   - owners: [uid]
4. Redirect to `/p/{personalSlug}`.

**Public visitor**:
- Can open `/p/{slug}` and read if page is public.

**Owner adding co-owner**:
- For MVP: owner enters another user’s UID/email.
  - If email: requires a lookup mapping email→uid (needs server/admin) or invite flow.
- Recommendation: implement `invites` with email tokens (see Open Questions).

---

## 9) Migration / Backfill Plan

### Phase 0: Prepare
- Add `pages` collection + basic page creation.
- Add `page_id` field to new memories.
- Keep reading legacy `user_id` for existing docs.

### Phase 1: Create personal pages for existing users
- For each distinct `user_id` in `memories`, create a personal page:
  - `page_id/slug`: e.g. `u-{user_id}` (or map if it’s already a Firebase uid)
  - `visibility`: `personal`
  - `owner_uids`: [user_id] (only if `user_id` is Firebase uid; otherwise needs mapping)

### Phase 2: Backfill memories
- For each memory with `user_id` and no `page_id`, set `page_id` to the created personal page.

### Phase 3: Cutover
- Update client and API to exclusively use `page_id`.
- Remove reliance on `user_id` (or keep as denormalized author uid, if desired).

Note: This migration assumes `user_id` is already a Firebase UID. If it isn’t, we need a mapping table or a one-time migration script.

---

## 10) Privacy & Security Considerations
- Ensure **personal pages are not readable** by non-owners.
- Ensure memory documents cannot be read directly unless page access is satisfied.
- Avoid storing sensitive PII in page slugs.
- Logging: do not log auth tokens or raw memory content (current README says this is already a goal).

---

## 11) Testing Strategy

### Unit tests
- Page creation enforces `owner_uids` non-empty.
- Ownership checks for memory CRUD.
- Slug uniqueness.

### Security rules tests
- Anonymous read works for public page memories.
- Anonymous read denied for personal page.
- Owner read/write allowed.
- Non-owner write denied.

### API integration
- Verify Firebase token auth.
- End-to-end: create page → add memory → list memories.

---

## 12) Rollout Plan
1. **Dual mode**: support legacy `/memories` endpoints + new page-scoped endpoints.
2. Update client to use page-scoped API.
3. Backfill `page_id` across existing memories.
4. Flip off legacy modes and remove `user_id` dependency.

---

## 13) Open Questions
1. Should “all pages are public” mean *discoverable* or just *readable if you have the URL*?
2. Should we support non-owner members now (viewer/editor), or only owners?
3. Best invite mechanism: email-based invites, UID-based, or “share link”?
4. Should slug be immutable (doc ID) or mutable (field + index)?
5. Should we store `created_by_uid` on memories separately from page ownership?
6. Do we need audit logs for ownership changes?
