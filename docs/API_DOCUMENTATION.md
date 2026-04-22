# API Documentation

## Base URLs

| Surface | Default Port | Description |
|---------|-------------|-------------|
| API server | 8074 | Canonical HTTP API, A2A endpoints, Admin UI, SPA |
| MCP server | 8076 | MCP tool contract interface |
| Web server | 8075 | Thin SPA delivery and API proxy |
| A2A server | 8077 | A2A compatibility surface (reuses API app) |

## Authentication

- **API key header:** `X-API-Key: <your-api-key>`
- **Bearer token:** `Authorization: Bearer <your-api-key>`
- **Cookie session:** `index_web_session` cookie set by `/auth/login`
- Administrative endpoints require `admin` role.
- Read operations require `reader`, `writer`, `maintainer`, or `admin`.
- Write operations require `writer`, `maintainer`, or `admin`.

## Canonical Metadata Contract

Search and retrieve responses, plus parser-oriented tool outputs, now expose the canonical metadata fields required by the metadata uplift work.

Core record identity and lifecycle fields:
- `doc_id`
- `record_id`
- `source_uri`
- `content_hash`
- `lifecycle_state`
- `is_latest`

Parser/OCR/table provenance fields:
- `parser_provider`
- `parser_version`
- `ocr_engine`
- `ocr_confidence`
- `page`
- `table_id`

OpenAPI verification surface:
- API OpenAPI: `http://127.0.0.1:8074/openapi.json`
- Web proxy OpenAPI: `http://127.0.0.1:8075/openapi.json`

Tool response notes:
- `ingest_preview` returns parser provenance plus OCR/table contract fields
- `table_extract` returns `parser_provider`, `page`, and `table_id` alongside extracted table payloads
- `search` and `retrieve` return canonical metadata through the response body and `metadata` object

## Verification Basis

- Source files reviewed: `src/index_server/api_server.py`, `src/index_server/web_server.py`, `src/index_server/mcp_server.py`, `src/index_server/a2a_server.py`
- Route inventory confirmed against code at all `@app.get`, `@app.post`, `@app.put`, `@app.delete`, `app.get(...)`, `app.post(...)`, `app.put(...)`, `app.delete(...)`, `app.api_route(...)`, `app.include_router(...)`, and `app.mount(...)` call sites.

---

## API Server Route Inventory

The API server (`api_server.py`) is the canonical surface. The A2A server (`a2a_server.py`) exposes the identical app.

### Authentication

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 1 | POST | `/auth/login` | `auth_login` | Authenticate with username/password; sets session cookie |
| 2 | GET | `/auth/me` | `auth_me` | Return current authenticated user from session cookie |
| 3 | POST | `/auth/logout` | `auth_logout` | Invalidate session cookie |

### Platform Health (via `create_health_router`)

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 4 | GET | `/health` | `health` (health router) | Service health with DB/VDB/embedding probes |
| 5 | GET | `/ready` | `ready` (health router) | Readiness probe |
| 6 | GET | `/live` | `live` (health router) | Liveness probe |

### Status, Logs, and Observability

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 7 | GET | `/status` | `status` | Runtime status metrics (overrides health router /status) |
| 8 | GET | `/api/status` | `status` | Alias for runtime status |
| 9 | GET | `/api/logs` | `logs` | Structured log entries for UI observability; accepts `phase`, `limit`, `level` params |
| 10 | GET | `/api/config-events` | `config_events` | Configuration change events for SPA views |
| 11 | GET | `/api/audit-log` | `api_audit_log` | Read JSONL audit/log entries; accepts `limit`, `log_source` params |

### Canonical API Health (`/api/v1`)

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 12 | GET | `/api/v1/health` | `health` | Canonical API health endpoint |

### A2A Endpoints

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 14 | GET | `/a2a` | `a2a_root` | A2A service descriptor (API-key auth required) |
| 15 | GET | `/a2a/health` | `a2a_health` | A2A health (API-key auth required) |
| 16 | GET | `/a2a/events` | `a2a_events` | A2A configuration change events |

### A2A Agent Card and Tasks (via `create_a2a_card_router`)

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 17 | GET | `/.well-known/agent.json` | `agent_card` | A2A agent card (skills: ingest_text, search, retrieve) |
| 18 | POST | `/tasks` | `submit_task` | Submit an A2A task |
| 19 | POST | `/a2a/tasks` | `submit_task` | Submit an A2A task (prefixed path) |

### Tool Catalogue and Execution (`/api/v1`)

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 20 | GET | `/api/v1/tools` | `list_tools` | List all registered tools with schemas |
| 21 | POST | `/api/v1/tools/{tool_name}` | `call_tool` | Execute a tool by name |
| 22 | GET | `/api/v1/tools/{tool_name}` | `call_tool` | Execute read-only status tools via GET |

### File Upload

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 26 | POST | `/api/v1/upload` | `upload_ingest` | Multipart file upload ingestion (profile, collection, metadata_json, upload) |

### Admin -- Profiles

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 28 | GET | `/admin/profiles` | `admin_profiles_list` | List all profiles |
| 29 | POST | `/admin/profiles` | `admin_profiles_create` | Create a profile (admin) |
| 30 | GET | `/admin/profiles/{profile_id}` | `admin_profiles_get` | Get profile details |
| 31 | PUT | `/admin/profiles/{profile_id}` | `admin_profiles_update` | Update a profile (admin) |
| 32 | DELETE | `/admin/profiles/{profile_id}` | `admin_profiles_delete` | Delete a profile (admin) |

### Admin -- Users

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 33 | GET | `/admin/users` | `admin_users_list` | List all users (admin) |
| 34 | POST | `/admin/users` | `admin_users_create` | Create a user (admin) |
| 35 | GET | `/admin/users/{user_id}` | `admin_users_get` | Get user details |
| 36 | PUT | `/admin/users/{user_id}` | `admin_users_update` | Update a user (admin) |
| 37 | DELETE | `/admin/users/{user_id}` | `admin_users_delete` | Delete a user (admin) |

### Admin -- Groups

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 38 | GET | `/admin/groups` | `admin_groups_list` | List all groups (admin) |
| 39 | POST | `/admin/groups` | `admin_groups_create` | Create a group (admin) |
| 40 | GET | `/admin/groups/{group_id}` | `admin_groups_get` | Get group details |
| 41 | PUT | `/admin/groups/{group_id}` | `admin_groups_update` | Update a group (admin) |
| 42 | DELETE | `/admin/groups/{group_id}` | `admin_groups_delete` | Delete a group (admin) |

### Admin -- API Keys

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 43 | GET | `/admin/api-keys` | `admin_api_keys_list` | List all API keys (admin) |
| 44 | POST | `/admin/api-keys` | `admin_api_keys_create` | Create an API key (admin) |
| 45 | DELETE | `/admin/api-keys/{key_id}` | `admin_api_keys_delete` | Revoke an API key (admin) |

### Admin -- Collections

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 46 | GET | `/admin/collections` | `admin_collections_list` | List collections (accepts `profile` query param) |
| 47 | POST | `/admin/collections` | `admin_collections_create` | Create a collection (admin) |
| 48 | GET | `/admin/collections/{collection_id}` | `admin_collections_get` | Get collection details (accepts `profile` query param) |
| 49 | PUT | `/admin/collections/{collection_id}` | `admin_collections_update` | Update a collection (admin) |
| 50 | DELETE | `/admin/collections/{collection_id}` | `admin_collections_delete` | Delete a collection (admin; accepts `profile` query param) |

### Admin -- Source Configs

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 51 | GET | `/admin/source-configs` | `admin_source_configs_list` | List source configurations |
| 52 | POST | `/admin/source-configs` | `admin_source_configs_create` | Create a source configuration (admin) |
| 53 | GET | `/admin/source-configs/{source_id}` | `admin_source_configs_get` | Get source configuration details |
| 54 | PUT | `/admin/source-configs/{source_id}` | `admin_source_configs_update` | Update a source configuration (admin) |
| 55 | DELETE | `/admin/source-configs/{source_id}` | `admin_source_configs_delete` | Delete a source configuration (admin) |

### Admin -- RBAC Bindings

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 56 | GET | `/admin/rbac-bindings` | `admin_rbac_bindings_list` | List all RBAC bindings (admin) |
| 57 | POST | `/admin/rbac-bindings` | `admin_rbac_bindings_create` | Create an RBAC binding (admin) |
| 58 | DELETE | `/admin/rbac-bindings/{entity_type}/{entity_id}/{role}` | `admin_rbac_bindings_delete` | Delete an RBAC binding (admin) |

### Admin UI (Legacy)

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 59 | GET | `/admin/ui` | `admin_ui_root` | Legacy admin UI root (profile management page) |
| 60 | GET | `/admin/ui/profiles` | `admin_ui_profiles` | Legacy admin profile management page |
| 61 | GET | `/admin/ui/security` | `admin_ui_security` | Legacy admin security management page |
| 62 | GET | `/admin/ui/app.js` | `admin_ui_app_js` | Legacy admin UI client script |
| 63 | GET | `/admin/ui/styles.css` | `admin_ui_styles_css` | Legacy admin UI stylesheet |

### SPA and Runtime Config

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 64 | GET | `/runtime-config.js` | `runtime_config` | SPA runtime configuration bootstrap script |
| 65 | GET | `/` | `spa_index` | SPA entrypoint (index.html) |
| 66 | GET | `/{path:path}` | `spa_fallback` | SPA client-side routing fallback |

### Static Assets

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 67 | -- | `/assets/**` | StaticFiles mount | Built SPA asset files |

---

## Web Server Route Inventory

The web server (`web_server.py`) is a thin SPA delivery and API proxy surface.

### Health and Status

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 1 | GET | `/health` | `health` | Web surface health check |
| 2 | GET | `/status` | `status` | Web surface status with backend URLs |

### Runtime Config

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 3 | GET | `/runtime-config.js` | `runtime_config` | SPA runtime config bootstrap |

### API Proxy Routes

| # | Methods | Path | Handler | Description |
|---|---------|------|---------|-------------|
| 4 | GET, POST, PUT, PATCH, DELETE | `/webapi/proxy/{path:path}` | `web_api_proxy` | Proxy JSON API requests to API server |
| 5 | GET, POST, PUT, PATCH, DELETE | `/api/{path:path}` | `api_proxy` | Proxy `/api/` requests to API server |
| 6 | GET, POST, PUT, PATCH, DELETE | `/app/{path:path}` | `app_proxy` | Proxy `/app/` requests to API server |
| 7 | GET, POST, PUT, PATCH, DELETE | `/admin/{path:path}` | `admin_proxy` | Proxy `/admin/` requests to API server (non-SPA paths) |
| 8 | GET, POST | `/auth/{path:path}` | `auth_proxy` | Proxy `/auth/` requests to API server |

### Documentation Proxy

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 9 | GET | `/openapi.json` | `openapi_proxy` | Proxy OpenAPI spec from API server |
| 10 | GET | `/docs` | `docs_proxy` | Proxy Swagger UI from API server |
| 11 | GET | `/redoc` | `redoc_proxy` | Proxy ReDoc from API server |

### Admin SPA Routes

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 12 | GET | `/admin` | `admin_spa_routes` | SPA entrypoint for admin root |
| 13 | GET | `/admin/users` | `admin_spa_routes` | SPA entrypoint for admin users |
| 14 | GET | `/admin/groups` | `admin_spa_routes` | SPA entrypoint for admin groups |
| 15 | GET | `/admin/api-keys` | `admin_spa_routes` | SPA entrypoint for admin API keys |
| 16 | GET | `/admin/rbac` | `admin_spa_routes` | SPA entrypoint for admin RBAC |

### SPA Entrypoint

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 17 | GET | `/` | `spa_root` | SPA root |
| 18 | GET | `/{path:path}` | `spa_fallback` | SPA client-side routing fallback |

### Static Assets

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 19 | -- | `/assets/**` | StaticFiles mount | Built SPA asset files |

---

## MCP Server Route Inventory

The MCP server (`mcp_server.py`) exposes MCP tool contracts and platform health.

| # | Method | Path | Handler | Description |
|---|--------|------|---------|-------------|
| 1 | GET | `/health` | health router | Service health probe |
| 2 | GET | `/ready` | health router | Readiness probe |
| 3 | GET | `/live` | health router | Liveness probe |
| 4 | -- | `/mcp` | MCP contract | MCP tool contract endpoint (via `register_mcp_contract`) |

---

## Canonical Metadata Contract (W28A-886)

The service now uses `cloud_dog_vdb` canonical metadata helpers for ingest-time identity and metadata validation.

### Ingest-time canonical fields

For `ingest_text`, `ingest_upload`, and `ingest_reference`, the persisted metadata now includes canonical fields derived from the package helpers:

- `doc_id`
- `record_id`
- `chunk_id`
- `source_uri`
- `content_hash`
- `source_hash`
- `lifecycle_state`
- `is_latest`
- `tenant_id`
- `namespace`

The service normalises source identifiers and computes deterministic IDs from canonical metadata inputs. Caller-supplied metadata remains additive, but identity/hash/lifecycle fields are package-owned and are not overridden by request payloads.

### Search response contract

`search` results now include the canonical retrieval fields at top level while preserving the full metadata map for backward compatibility:

```json
{
  "doc_id": "<canonical-doc-id>",
  "record_id": "<canonical-record-id>",
  "chunk_id": "<canonical-chunk-id>",
  "text": "<chunk text>",
  "score": 0.0,
  "source_uri": "<canonical-source-uri>",
  "content_hash": "<canonical-content-hash>",
  "lifecycle_state": "active",
  "is_latest": true,
  "metadata": { "...": "..." }
}
```

Search requests still accept `filters`, but the service now enforces metadata filters again on returned rows so caller-visible results stay consistent even if a backend planner or backend search implementation is broader than requested.

### Retrieve response contract

`retrieve` now returns canonical identity/lifecycle fields in addition to the existing payload:

```json
{
  "doc_id": "<canonical-doc-id>",
  "record_id": "<canonical-record-id>",
  "profile": "default",
  "collection": "example",
  "source": "<source-uri>",
  "source_uri": "<canonical-source-uri>",
  "text": "<stored text>",
  "content_hash": "<canonical-content-hash>",
  "lifecycle_state": "active",
  "is_latest": true,
  "metadata": { "...": "..." }
}
```

### Delete and retention semantics

- `delete_by_id` resolves canonical record identity and marks local state as `lifecycle_state=deleted`
- superseded records are marked through canonical lifecycle helpers during re-ingest/version transitions
- local search excludes deleted records by lifecycle state
| 5 | -- | `/mcp/tools` | MCP contract | MCP tool catalogue |
| 6 | POST | `/mcp/tools/{tool_name}` | per-tool handler | Execute individual MCP tool (auth-enforced) |

Each tool registered in the shared tool registry is exposed as `POST /mcp/tools/{tool_name}` with authentication and RBAC enforcement.

---

## Example Requests

### Health Check
```bash
curl http://localhost:8083/health
```

### Authenticate
```bash
curl -X POST http://localhost:8083/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

### List Tools (API key auth)
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8083/api/v1/tools
```

### Execute a Tool
```bash
curl -X POST http://localhost:8083/api/v1/tools/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "search terms", "profile": "default", "collection": "my_collection"}'
```

### File Upload Ingestion
```bash
curl -X POST http://localhost:8083/api/v1/upload \
  -H "X-API-Key: your-api-key" \
  -F "profile=default" \
  -F "collection=my_collection" \
  -F "metadata_json={}" \
  -F "upload=@document.pdf"
```

### Admin: List Profiles
```bash
curl -H "X-API-Key: your-admin-key" http://localhost:8083/admin/profiles
```

### Audit Log
```bash
curl -H "X-API-Key: your-api-key" "http://localhost:8083/api/audit-log?limit=50&log_source=audit"
```

## Summary

| Surface | Total Routes |
|---------|-------------|
| API server | 67 |
| Web server | 19 |
| MCP server | 6+ (health + per-tool) |
| **Total unique route registrations** | **92+** |
