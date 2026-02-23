# Design Doc — Issue #41: Change Page from Static to Web App

## 0) Context / Problem Statement

The front-end today is a single static HTML file (`client/index.html`) deployed to
GitHub Pages. It reads Firestore directly via the Firebase Web SDK and displays
memories for a hardcoded `user_id` (overridable via `?user_id=` query param).

Issue #34 introduced multi-user identity, pages with ownership, and visibility
(public/personal). The backend API now supports page-scoped memory CRUD with
Firebase Auth. However, the front-end has no routing, no navigation, and no
awareness of pages or ownership.

Issue #41 bridges this gap: **replace the static page with a web app** that
supports login, per-user dashboards, and page-based URLs.

---

## 1) Goals

### Functional
1. **Authenticated experience**: Users sign in with Google (Firebase Auth) and see
   a dashboard of their pages.
2. **Personal page**: Each user sees their own personal page after sign-in.
3. **Owned pages**: Users see a list of all pages they own.
4. **Page URLs**: Each page has a stable, shareable URL (`/p/{slug}`).
5. **Public page viewing**: Any signed-in user can view a public page by URL
   (public pages are readable but not discoverable).
6. **Data via API**: The web app fetches data through the Cloud Run API (not
   directly from Firestore), establishing a clean client→API→Firestore boundary.

### Non-goals (for this issue)
- Page creation UI (separate issue).
- Page settings / management UI (invite links, visibility toggle, etc.).
- Anonymous (logged-out) access to public pages. (Can be added later.)
- Mobile-native app or PWA features.
- Search / discovery of public pages.
- Offline support.

---

## 2) Architecture Decision: Framework & Hosting

### Framework: React + Vite (SPA)

**Choice:** Single-page application using React with Vite as the build tool.

**Rationale:**
- **Simplicity**: An SPA with client-side routing matches the current model
  (single HTML file + Firebase SDK). No server-side rendering needed — all data
  comes from the existing Cloud Run API.
- **Vite**: Fast builds, zero-config for React, excellent dev experience.
  Produces a static bundle (HTML + JS + CSS) that can be hosted anywhere.
- **React**: Widely adopted, good ecosystem for routing (`react-router`) and
  data fetching. The team is familiar with it.
- **No Next.js**: SSR/SSG adds deployment complexity (needs a Node server or
  edge runtime) without clear benefit — our pages are dynamic (fetched per
  request from the API) and we don't need SEO for personal/private pages.

### Hosting: Firebase Hosting

**Choice:** Deploy the SPA to Firebase Hosting with rewrites to the Cloud Run API.

**Rationale:**
- **Unified Firebase stack**: The project already uses Firebase Auth and
  Firestore. Firebase Hosting keeps the entire frontend infrastructure on
  Google Cloud, simplifying configuration (auth redirect URIs, CORS).
- **Built-in SPA support**: Firebase Hosting natively supports SPA rewrites —
  all unmatched routes serve `index.html` without workarounds like `404.html`.
- **API rewrites**: `firebase.json` can proxy `/api/**` requests to the Cloud
  Run API, eliminating CORS configuration entirely. The browser sees a single
  origin.
- **Free tier**: Firebase Hosting's free tier (Spark plan) is generous for our
  traffic (10 GB/month transfer, 1 GB storage).
- **Preview channels**: Firebase Hosting supports preview URLs per PR, useful
  for reviewing frontend changes before merge.

**Alternative considered:** GitHub Pages — rejected because it requires
`404.html` hacks for SPA routing, cannot proxy API requests (requires CORS),
and splits infrastructure across GitHub and Google Cloud.

### API: Existing Cloud Run API

The web app calls the existing Cloud Run REST API (`src/api.py`). One new
endpoint is needed (see §6).

---

## 3) Routing & URL Structure

All routes are handled client-side by `react-router`.

| Route | View | Auth required? |
|---|---|---|
| `/` | Landing / redirect | No |
| `/sign-in` | Google sign-in | No |
| `/dashboard` | User's home (list of owned pages) | Yes |
| `/p/{slug}` | Page view (memories list) | Depends on visibility |

### Route details

- **`/`** — If signed in, redirect to `/dashboard`. If not, show a minimal
  landing with a "Sign in" button.
- **`/sign-in`** — Triggers Google sign-in (Firebase Auth popup). On success,
  redirects to `/dashboard`.
- **`/dashboard`** — Shows the user's personal page (if any) prominently, plus a
  list of all owned pages. Each page is a link to `/p/{slug}`.
- **`/p/{slug}`** — Displays a page's memories. Public pages are viewable by any
  signed-in user. Personal pages show a 403 message to non-owners.

### SPA fallback

Firebase Hosting natively supports SPA routing via the `rewrites` config in
`firebase.json`. All unmatched routes serve `index.html` — no workarounds
needed.

---

## 4) Auth Model

### Client-side auth flow

1. Firebase Auth SDK handles Google sign-in (popup with redirect fallback).
2. On auth state change, store the Firebase `User` object in React context.
3. For API calls, obtain a fresh ID token via `user.getIdToken()` and send it
   as `Authorization: Bearer <token>`.

### Protected routes

A `<RequireAuth>` wrapper component checks auth state:
- If signed in → render children.
- If not signed in → redirect to `/sign-in`.
- While loading auth state → show a spinner.

### Token refresh

Firebase ID tokens expire after 1 hour. `getIdToken(true)` forces a refresh.
The API client should retry once on 401 responses with a refreshed token.

---

## 5) Screen List & Components

### 5.1 Screens

**Landing (`/`)**
- Logo / app name.
- "Sign in with Google" button (if not signed in).
- Auto-redirect to `/dashboard` if already signed in.

**Sign-in (`/sign-in`)**
- Triggers Firebase Google sign-in.
- On success, calls `GET /users/me` to ensure user profile exists, then
  redirects to `/dashboard`.

**Dashboard (`/dashboard`)**
- **Header**: App name, user avatar/name, sign-out button.
- **Personal page section**: Link to the user's personal page (from
  `user.default_personal_page_id`). If none exists, show a placeholder
  (page creation is out of scope for this issue).
- **My pages list**: Cards/links for each page the user owns. Each card shows
  the page title, visibility badge (public/personal), and links to `/p/{slug}`.

**Page view (`/p/{slug}`)**
- **Header**: Page title, visibility badge, back-to-dashboard link.
- **Memories list**: Two sections — "This Week" and "Upcoming" (same logic as
  current `client/index.html`). Each memory shows title, date, time, place,
  content (with inline markdown links), and attachments.
- **Empty state**: "No upcoming events" message.
- **Error states**: 404 (page not found), 403 (not authorized for personal page).

### 5.2 Shared components

- `<AppShell>` — Layout wrapper: nav bar + content area.
- `<NavBar>` — App name (links to `/dashboard`), user avatar, sign-out.
- `<RequireAuth>` — Auth guard (redirect to `/sign-in` if not signed in).
- `<PageCard>` — Page summary card for the dashboard list.
- `<MemoryCard>` — Single memory display (title, date, time, place, content).
- `<MemoryList>` — Groups memories into "This Week" / "Upcoming" sections.
- `<LoadingSpinner>` — Shown during data fetches and auth state resolution.
- `<ErrorMessage>` — Generic error display (404, 403, network errors).

---

## 6) API Contract Usage

### Existing endpoints the web app calls

| Endpoint | Used by | Purpose |
|---|---|---|
| `GET /users/me` | Sign-in flow, dashboard | Get/create user profile |
| `GET /pages/{slug}` | Page view | Fetch page metadata |
| `GET /pages/{slug}/memories` | Page view | List memories for a page |

### New endpoint needed

**`GET /users/me/pages`** — List pages owned by the authenticated user.

This wraps the existing `page_storage.list_pages_for_user(uid)` function,
which already exists but is not exposed via an API endpoint.

```
GET /users/me/pages
Authorization: Bearer <firebase_id_token>

200 OK
{
  "pages": [
    {
      "slug": "my-family",
      "title": "My Family",
      "visibility": "public",
      "owner_uids": ["uid1"],
      "created_at": "...",
      "updated_at": "..."
    },
    ...
  ]
}
```

### API client pattern

A thin API client module (`src/api.ts` or similar) that:
- Wraps `fetch()` calls to the Cloud Run API base URL.
- Attaches `Authorization: Bearer <token>` from Firebase Auth.
- Handles 401 by refreshing the token and retrying once.
- Throws typed errors for 403, 404, and network failures.

The API base URL is configured via an environment variable
(`VITE_API_BASE_URL`) at build time.

---

## 7) Data Fetching Patterns

### Approach: Fetch on route entry

Each screen fetches its data when it mounts. No global state management library
(Redux, Zustand) — React's built-in `useState` + `useEffect` is sufficient for
this scope.

### Caching

No client-side cache for MVP. Each navigation fetches fresh data. This is
acceptable because:
- The data set is small (tens of memories per page).
- The API is fast (Firestore reads are low-latency).
- We avoid cache invalidation complexity.

If performance becomes an issue later, we can add `react-query` or SWR.

### Loading states

Every data-fetching component manages three states:
- `loading: boolean` — show spinner.
- `data: T | null` — render content.
- `error: Error | null` — show error message.

---

## 8) Error States

| Scenario | User sees |
|---|---|
| Network error / API unreachable | "Unable to connect. Please try again." with retry button. |
| 401 (token expired, refresh failed) | Redirect to `/sign-in`. |
| 403 on personal page | "This page is private." |
| 404 page not found | "Page not found." with link back to dashboard. |
| No personal page exists | Placeholder on dashboard: "You don't have a personal page yet." |
| No owned pages | Dashboard shows only the personal page section (or placeholder if none). |
| Empty page (no memories) | "No upcoming events on this page." |

---

## 9) Project Structure

```
web/                          # New directory (replaces client/)
├── index.html                # Vite entry point
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx              # React entry, router setup
│   ├── api.ts                # API client (fetch wrapper)
│   ├── auth.tsx              # Firebase Auth provider + hooks
│   ├── routes/
│   │   ├── Landing.tsx
│   │   ├── SignIn.tsx
│   │   ├── Dashboard.tsx
│   │   └── PageView.tsx
│   └── components/
│       ├── AppShell.tsx
│       ├── NavBar.tsx
│       ├── RequireAuth.tsx
│       ├── PageCard.tsx
│       ├── MemoryCard.tsx
│       ├── MemoryList.tsx
│       ├── LoadingSpinner.tsx
│       └── ErrorMessage.tsx
├── firebase.json             # Hosting config (rewrites, public dir)
└── public/
```

The `web/` directory is self-contained with its own `package.json`. The Python
backend is unaffected.

---

## 10) Deployment Plan & Incremental Rollout

### Phase 1: Scaffold & deploy skeleton (keep existing static page)

1. Create `web/` directory with Vite + React + TypeScript setup.
2. Implement routing skeleton (all four routes with placeholder content).
3. Set up Firebase Auth (sign-in / sign-out).
4. Configure `firebase.json` with hosting settings and API rewrites.
5. Deploy to Firebase Hosting via CI.
6. **Keep `client/index.html` accessible** at `/legacy.html` during rollout.
   The CI workflow deploys it alongside the new build output.

### Phase 2: Core screens

1. Add the new `GET /users/me/pages` API endpoint.
2. Implement Dashboard (fetch user + pages, render list).
3. Implement Page View (fetch page metadata + memories, render with
   This Week / Upcoming grouping).
4. Port the memory rendering logic from `client/index.html` (markdown links,
   details expand, attachments).

### Phase 3: Polish & cutover

1. Error states and loading states for all screens.
2. Basic responsive styling (mobile-friendly).
3. Test across browsers.
4. Remove `client/index.html` legacy fallback once the new app is confirmed
   working.

### Firebase Hosting configuration

`web/firebase.json`:
```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "living-memory-api",
          "region": "us-east1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

The `/api/**` rewrite proxies API calls to the Cloud Run service, so the
browser sees a single origin and no CORS headers are needed.

### CI/CD changes

Replace the GitHub Pages deployment in `.github/workflows/publish.yml` with
Firebase Hosting deployment:
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: 20
- run: cd web && npm ci && npm run build
- uses: FirebaseExtended/action-hosting-deploy@v0
  with:
    repoToken: '${{ secrets.GITHUB_TOKEN }}'
    firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
    channelId: live
    projectId: <firebase-project-id>
```

For PR previews, the same action with `channelId: pr-${{ github.event.number }}`
deploys to a preview channel URL.

### Local development

```bash
cd web
npm install
npm run dev          # Vite dev server on localhost:5173
```

The Vite dev server proxies `/api` to the local Cloud Run API
(`http://localhost:8000`) via `vite.config.ts`:
```ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

### Environment configuration

| Variable | Build-time / Runtime | Purpose |
|---|---|---|
| `VITE_FIREBASE_CONFIG` | Build-time | Firebase project config (JSON string) |
| `VITE_API_BASE_URL` | Build-time | API base URL (empty string when using Firebase Hosting rewrites; set to Cloud Run URL for local dev without proxy) |

---

## 11) Test Plan

### Unit tests (Vitest)

- **API client**: Mock `fetch`, verify correct headers, token refresh on 401.
- **Auth hooks**: Mock Firebase Auth, verify sign-in/sign-out state transitions.
- **MemoryList grouping**: Verify "This Week" / "Upcoming" split logic.

### Component tests (React Testing Library)

- **RequireAuth**: Renders children when signed in, redirects when not.
- **Dashboard**: Renders page list from mocked API response.
- **PageView**: Renders memories; shows 403/404 for error responses.

### Smoke test (manual / CI)

- Build succeeds (`npm run build` in CI).
- Firebase Hosting deploy succeeds; `index.html` is present in build output.
- App loads at `/`, redirects to `/sign-in`, sign-in works, dashboard shows
  pages, page view shows memories.
- API rewrite (`/api/**` → Cloud Run) works correctly.

### E2E (future, not required for initial merge)

- Playwright or Cypress tests against a staging environment with the Firebase
  Auth emulator and a test API instance.

---

## 12) Open Questions

1. **Styling approach**: Tailwind CSS, CSS modules, or a component library
   (e.g. Radix, shadcn/ui)? Recommendation: Tailwind for speed, but open to
   team preference.

2. **Anonymous access to public pages**: Issue #41 says "a user can view a
   public page when logged in." Should we also allow logged-out users to view
   public pages (read-only, no dashboard)? The API already supports it
   (`GET /pages/{slug}` and `GET /pages/{slug}/memories` don't require auth
   for public pages). Deferring for now.

3. **Legacy `client/index.html` timeline**: How long do we keep the legacy page
   accessible alongside the new app? Suggestion: remove it one release after
   the web app is stable.

4. **Custom domain**: Is the app served from a custom domain or the default
   Firebase Hosting URL? Firebase Hosting supports custom domains via the
   console. This affects Firebase Auth redirect URIs.
