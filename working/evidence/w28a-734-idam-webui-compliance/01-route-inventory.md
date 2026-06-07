# W28A-734 — 01 Route Inventory

## Before (baseline @ 872-R2 tip 2a4b7b9 / service main b164abd)

UI app `apps/index-retriever/src/routes/App.tsx`:
- nav + `<Route>`: `/admin/users`, `/admin/groups`, `/admin/api-keys`, `/admin/rbac` only. No `/idam/*`.

Service `src/index_server/web_server.py`:
- `admin_spa_routes` served `/admin`, `/admin/users`, `/admin/groups`, `/admin/api-keys`, `/admin/rbac`.
- `_SPA_ADMIN_PATHS` contained only the `admin/*` set.

## After (this lane)

UI `App.tsx` (commit 1dfa247):
- Canonical: `<Route path="/idam">` → redirect `/idam/users`; `/idam/users`, `/idam/groups`, `/idam/api-keys`, `/idam/rbac` render UsersPage/GroupsPage/ApiKeysPage/RbacPage.
- Nav "Admin" group points at `/idam/*`.
- Legacy `/admin/*` retained as `<Navigate>` alias redirects to `/idam/*` (PS-71 71-idam-webui.md route lock allows aliases that mount the same component).

Service `web_server.py` (commit 22446fe):
- `admin_spa_routes` now also serves `/idam`, `/idam/users`, `/idam/groups`, `/idam/api-keys`, `/idam/rbac` (SPA index.html).
- `_SPA_ADMIN_PATHS` extended with the `idam/*` set for deep-link refresh via the catch-all `spa_fallback`.

## Live verification (Python web server, port 8075)

```
/idam/users     -> HTTP 200 (text/html)
/idam/groups    -> HTTP 200 (text/html)
/idam/api-keys  -> HTTP 200 (text/html)
/idam/rbac      -> HTTP 200 (text/html)
/admin/users    -> HTTP 200 (text/html)   (legacy alias still served)
```

Via vite preview (port 5197, SPA fallback) the `/idam/*` routes render the React pages and the
Playwright conformance suite drives them (see 03-playwright-matrix.md).

## Note — instruction scope vs PS-71 standard

`71-idam-webui.md` canonical set is 5 pages (adds `/idam/roles`, IW3A). The W28A-734 instruction
explicitly scopes 4 (`users`/`groups`/`api-keys`/`rbac`). This lane delivers the 4 named pages; the
Roles page (IW3A) is flagged for a coordinator decision / separate lane and is not silently absorbed.
