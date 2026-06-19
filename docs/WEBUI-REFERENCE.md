---
template-id: T-WUI
template-version: 1.0
applies-to: docs/WEBUI-REFERENCE.md
registry: service
required: conditional
when-applicable: "service ships a WebUI SPA (ui/dist; cloud-dog-ai-ui-monorepo/apps/index-retriever)"
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 16fd5b2c0000000000000000000000000000000000
doc-git-branch: main
doc-source-shas:
  - src/index_server/web_server.py
  - src/index_server/admin_ui.py
  - ui/dist/index.html
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T00:00:00Z
---

# index-retriever-mcp-server — WEBUI-REFERENCE

> **Template version:** T-WUI v1.0 — conditional: service ships a WebUI SPA.

The index-retriever WebUI is a React SPA (Vite/Tailwind) served from `ui/dist/index.html`
by the web tier (port `8075`, `CLOUD_DOG__WEB_SERVER__PORT`). The SPA delegates all data
operations to the API server via the web-tier proxy at `/webapi/proxy/` and `/api/`. Static
admin pages (profiles, collections, security, document-structure) are rendered server-side
by `src/index_server/admin_ui.py` for lightweight HTMX-style use. The monorepo source is at
`cloud-dog-ai-ui-monorepo/apps/index-retriever`.

## 1. Panel structure

All SPA routes serve `ui/dist/index.html` (catch-all) except the static admin pages at
`/collections`, `/admin*`, and the API/A2A proxies. Static routes defined in
`src/index_server/web_server.py:_SPA_ADMIN_PATHS` + `_SPA_RESERVED_SEGMENTS`.

| Route | Panel | Roles | Backend route |
|---|---|---|---|
| `/` | → `/dashboard` (redirect) | any authenticated | — |
| `/login` | → `/dashboard` after auth | any | — |
| `/dashboard` | DashboardPage — service overview, health, queue status | viewer + | `/api/status`, `/api/v1/health` |
| `/profiles` | ProfileCrudPage — profile CRUD | admin (write), viewer (read) | `/api/v1/admin/profiles/`, `/api/v1/profiles` |
| `/collections` | Static HTML collections inventory (admin_ui.py) | viewer + | `/api/v1/collections` |
| `/source-config` | SourceConfigPage — source config CRUD ("File Ingest") | user (`source.configure`) | `/api/v1/admin/source-configs/`, `/api/v1/source-configs` |
| `/ingest-search` | IngestSearchPage — upload, ingest text, search, retrieve ("Search Retrieve") | user (ingest), viewer (search) | `/api/v1/ingest/upload`, `/api/v1/search` |
| `/retention-delete` | RetentionDeletePage — retention, delete, reindex ("Retention Delete") | admin/user | `/api/v1/retention/run`, `/api/v1/delete` |
| `/jobs` | JobsPageView — job list, cancel, retry | user | `/api/v1/jobs` |
| `/observability` | ObservabilityPage — audit log, config events | admin/audit-log | `/api/logs`, `/api/audit-log`, `/api/config-events` |
| `/mcp-console` | McpConsolePage — interactive MCP tool dispatcher | user | `/api/v1/tools`, `/mcp` |
| `/a2a-console` | A2aConsolePage — A2A event console | user | `/a2a`, `/a2a/events` |
| `/api-docs` | ApiDocsPage — Swagger/OpenAPI browser | viewer + | `/openapi.json`, `/docs` |
| `/settings` | SettingsPage — masked effective config | viewer (own) | `/api/config`, `/auth/me` |
| `/idam/users` | IdamUsersPage — user CRUD | admin (all), user (own row) | `/admin/users` |
| `/idam/groups` | IdamGroupsPage — group + membership CRUD (cascade source) | admin / group-admin | `/admin/groups` |
| `/idam/api-keys` | IdamApiKeysPage — API key CRUD | admin (all), user (own) | `/admin/api-keys` |
| `/idam/roles` | IdamRolesPage — role catalog view | admin | `/api/v1/admin/roles` |
| `/idam/rbac` | IdamRbacPage — RBAC binding editor (cascade write surface) | admin / group-admin | `/admin/rbac` |
| `/security` | → `/idam/users` (deprecated alias) | — | redirect |
| `/admin` | → `/idam/users` (legacy gateway) | — | redirect |
| `/admin/users` | IdamUsersPage (legacy path) | admin | `/admin/users` |
| `/admin/groups` | IdamGroupsPage (legacy path) | admin | `/admin/groups` |
| `/admin/api-keys` | IdamApiKeysPage (legacy path) | admin | `/admin/api-keys` |
| `/admin/roles` | IdamRolesPage (legacy path) | admin | `/api/v1/admin/roles` |
| `/admin/rbac` | IdamRbacPage (legacy path) | admin | `/admin/rbac` |

## 2. Login

**Flow:** cookie-based login (username + password). The SPA posts credentials to
`/auth/login`; the API server issues a session cookie. The web tier forwards all
`/auth/*` requests verbatim with the caller's own session (never injects the service
api-key on auth paths — `W28A-734-R2` security gate).

**Session storage:** HTTP-only session cookie set by `cloud_dog_idam`. Expires per idam
session TTL. No token stored in `localStorage`.

**Logout:** POST `/auth/logout` clears the session cookie and redirects to `/login`.

**Bootstrap:** first-run admin account seeded by `cloud_dog_idam` on first deploy. Flat
demo principals (`admin/read-write/read-only`) are seeded at startup for development.

**AGENT-LESSONS trap:** auth mode is `cookie` for the WebUI — `_web_auth_mode` in
`src/index_server/admin_ui.py` returns `"cookie"` regardless of the API auth mode
(`apikey+jwt`). Do not flip WebUI login to `api_key`.

## 3. RBAC visibility matrix

| Panel | admin | read-write (user) | read-only (viewer) | anon |
|---|---|---|---|---|
| Dashboard | full view | full view | full view | 401 |
| Profiles | create/update/delete + list | list only | list only | 401 |
| Collections (static) | full | full | list only | 401 |
| Source Config | full CRUD | own configs | list only | 401 |
| Ingest & Search | ingest + search | ingest + search | search/retrieve only | 401 |
| Retention & Delete | full | delete + retention | — (403) | 401 |
| Jobs | list + cancel + retry + delete | list + cancel + retry | — (403) | 401 |
| Observability | full audit log | — (403) | — (403) | 401 |
| MCP Console | all 94 tools | write tools | read tools | 401 |
| A2A Console | full | full | read | 401 |
| API Docs | full | full | full | 401 |
| Settings | own + all (masked) | own (masked) | own (masked) | 401 |
| IDAM / Users | full CRUD | own row only | own row only | 401 |
| IDAM / Groups | full CRUD | — (403) | — (403) | 401 |
| IDAM / API Keys | full CRUD | own keys | own keys | 401 |
| IDAM / Roles | read | — (403) | — (403) | 401 |
| IDAM / RBAC | full bindings CRUD | — (403) | — (403) | 401 |

## 4. Static routes

Static HTML admin pages (rendered by `src/index_server/admin_ui.py`, no SPA bundle needed):

| Path | Page function | Description |
|---|---|---|
| `/collections` | `collections_page()` | HTML collection inventory table |
| `/admin` | → `_spa_index()` | legacy gateway (SPA handles) |
| `/admin/users` | → `_spa_index()` | IDAM users (SPA handles) |
| `/admin/groups` | → `_spa_index()` | IDAM groups (SPA handles) |
| `/admin/api-keys` | → `_spa_index()` | IDAM api-keys (SPA handles) |
| `/admin/rbac` | → `_spa_index()` | RBAC bindings (SPA handles) |

Reserved path segments that return `404` if no static file matches (never fall through to
SPA index): `api`, `app`, `a2a`, `mcp`, `auth`, `assets`, `health`, `runtime-config.js`,
`docs`, `openapi.json`, `redoc`, `webapi`, `status`.

## 5. Cross-references

- [API-REFERENCE.md](API-REFERENCE.md)
- [ROLES-AND-USECASES.md](ROLES-AND-USECASES.md)
- PS-77-webui-comprehensive.md
- PS-30-ui.md
- Source: `src/index_server/web_server.py`
- Source: `src/index_server/admin_ui.py`
- Monorepo app: `cloud-dog-ai-ui-monorepo/apps/index-retriever/src/routes/App.tsx`

## 6. Project-specific notes

The web tier (`web_server.py`) runs on port `8075` and proxies:
- `/api/*` → API server (port `8074`)
- `/mcp` → MCP server (port `8076`)
- `/a2a/*` → A2A server (port `8077`)
- `/auth/*` → API server (forwarded verbatim, no service api-key injection)
- `/admin/*` → API server (forwarded with caller auth, not service api-key — W28A-734-R2)
- `/webapi/proxy/{path}` → generic proxy for WebUI admin pages

The SPA `runtime-config.js` is served at `/runtime-config.js` and holds the API base URL
for runtime configuration. The example is at `ui/dist/runtime-config.example.js`.

Flat demo principals are seeded at startup: `admin` (full), `read-write` (user/write),
`read-only` (viewer/read). Canonical passwords sourced from Vault at
`cloud_dog_ai/config.dev.services.index-retriever` (see `DEPLOY.md`).
