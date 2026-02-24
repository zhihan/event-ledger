# Plan: Issue #35 — Page Admin Functionality

## Goal

Add page admin capabilities: rename pages, soft-delete pages (with 30-day grace
period), and clean up soft-deleted pages in the existing cleanup job.

## What Already Exists

| Feature | Storage (`page_storage.py`) | API (`api.py`) |
|---|---|---|
| Create page | `create_page()` | `POST /pages` |
| Get page | `get_page()` | `GET /pages/{slug}` |
| Update page | `update_page()` | **no endpoint** |
| Delete page | `delete_page()` (hard delete) | **no endpoint** |
| Invite CRUD | full | full |
| Multi-owner | `add_owner()` / `remove_owner()` | `DELETE /pages/{slug}/owners/{uid}` |

## Changes

### 1. Add `delete_after` field to `Page` dataclass

**File:** `src/page_storage.py`

Add an optional `delete_after: datetime | None = None` field to the `Page`
dataclass. Update `to_dict()` and `from_dict()` to serialize/deserialize it.

```python
@dataclass
class Page:
    slug: str
    title: str
    visibility: str
    owner_uids: list[str]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    description: str | None = None
    delete_after: datetime | None = None  # NEW — set by soft-delete

    def to_dict(self) -> dict:
        now = _utcnow()
        return {
            "title": self.title,
            "description": self.description,
            "visibility": self.visibility,
            "owner_uids": self.owner_uids,
            "created_at": self.created_at or now,
            "updated_at": self.updated_at or now,
            "delete_after": self.delete_after,  # NEW
        }

    @classmethod
    def from_dict(cls, slug: str, data: dict) -> Page:
        return cls(
            ...,
            delete_after=data.get("delete_after"),  # NEW
        )
```

### 2. Add `soft_delete_page()` helper

**File:** `src/page_storage.py`

```python
def soft_delete_page(slug: str) -> Page:
    """Soft-delete a page: set delete_after on page, expire all its memories."""
    import firestore_storage
    from datetime import date, timedelta

    deadline = _utcnow() + timedelta(days=30)
    expire_date = (date.today() + timedelta(days=30))

    # Expire all memories on this page
    pairs = firestore_storage.load_memories_by_page(slug)
    for doc_id, mem in pairs:
        mem.expires = expire_date
        firestore_storage.save_memory(mem, doc_id=doc_id, page_id=slug)

    # Mark the page itself for deletion
    return update_page(slug, {"delete_after": deadline})
```

### 3. `PATCH /pages/{slug}` — Rename / update page metadata

**File:** `src/api.py`

New request model:

```python
class UpdatePageRequest(BaseModel):
    title: str | None = None
    description: str | None = None
```

New endpoint:

```python
@app.patch("/pages/{slug}")
def update_page(slug: str, body: UpdatePageRequest, uid: str = Depends(_get_uid)):
    _require_page_owner(slug, uid)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        updated = page_storage.update_page(slug, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    page_storage.write_audit_log(
        page_slug=slug, action="page_updated", actor_uid=uid,
        metadata={"fields": list(updates.keys())},
    )
    return {"page": {**updated.to_dict(), "slug": updated.slug}}
```

### 4. `DELETE /pages/{slug}` — Soft-delete page

**File:** `src/api.py`

```python
@app.delete("/pages/{slug}")
def delete_page(slug: str, uid: str = Depends(_get_uid)):
    _require_page_owner(slug, uid)
    page_storage.soft_delete_page(slug)
    page_storage.write_audit_log(
        page_slug=slug, action="page_deleted", actor_uid=uid,
    )
    return {"ok": True}
```

### 5. Update cleanup job to purge soft-deleted pages

**File:** `src/cleanup.py`

After the existing `cleanup_firestore()` call, add logic to find and hard-delete
pages past their `delete_after` deadline:

```python
def cleanup_pages(now: datetime | None = None) -> list[str]:
    """Hard-delete pages whose delete_after has passed."""
    import page_storage

    if now is None:
        now = page_storage._utcnow()

    # Query all pages with delete_after set
    db = page_storage._get_client()
    docs = (
        db.collection(page_storage.PAGES_COLLECTION)
        .where("delete_after", "<=", now)
        .stream()
    )
    deleted_slugs = []
    for doc in docs:
        slug = doc.id
        page_storage.delete_page(slug)
        deleted_slugs.append(slug)
    return deleted_slugs
```

Wire it into `main()` so both expired memories and soft-deleted pages are cleaned
up in a single run.

### 6. Tests

**File:** `tests/test_api_pages.py` — add tests:

- `test_patch_page_rename` — PATCH with new title, verify 200 and updated title
- `test_patch_page_not_owner` — PATCH by non-owner returns 403
- `test_patch_page_empty_body` — PATCH with no fields returns 400
- `test_delete_page_soft` — DELETE sets `delete_after`, expires memories
- `test_delete_page_not_owner` — DELETE by non-owner returns 403

**File:** `tests/test_page_storage.py` — add tests:

- `test_soft_delete_page` — verifies `delete_after` is set, memories are expired
- `test_page_delete_after_roundtrip` — `to_dict()` / `from_dict()` with `delete_after`

**File:** `tests/test_cleanup.py` (or add to existing test file):

- `test_cleanup_pages` — pages past `delete_after` are hard-deleted
- `test_cleanup_pages_skips_active` — pages not yet past deadline are kept

## File Change Summary

| File | Change |
|---|---|
| `src/page_storage.py` | Add `delete_after` field to `Page`, add `soft_delete_page()` |
| `src/api.py` | Add `PATCH /pages/{slug}`, `DELETE /pages/{slug}`, `UpdatePageRequest` model |
| `src/cleanup.py` | Add `cleanup_pages()`, wire into `main()` |
| `tests/test_api_pages.py` | Tests for PATCH and DELETE endpoints |
| `tests/test_page_storage.py` | Tests for soft-delete and `delete_after` serialization |
| `tests/test_cleanup.py` | Tests for page cleanup |

## Verification

1. `pytest` — all existing tests still pass
2. New tests cover rename, soft-delete, and cleanup flows
3. Manual smoke test: create page, rename, soft-delete, verify `delete_after` set
