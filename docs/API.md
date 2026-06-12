# API — index-retriever-mcp-server

Canonical API/surface reference. Consolidates the former `API-REFERENCE.md`, `API-REFERENCE.md`, and
`MCP-REFERENCE.md` (preserved under `docs/archive/`). Machine spec: `docs/openapi.json`. Roles/parity:
`ROLES-AND-USECASES.md`. Built/reconciled by W28A-749 (IDAM Thread-b).

## Surfaces & canonical base paths (FR-01, FR-01A)
| Surface | Base path | Notes |
|---|---|---|
| HTTP API | `/api/v1` (Traefik strips `/api` → server sees `/v1`; legacy `/app/v1` compat) | `cloud_dog_api_kit` FastAPI factory; correlation IDs, structured errors, `/health` |
| MCP | `/mcp`; catalogue `GET /mcp/tools` | JSON-RPC 2.0; `initialize` handshake required |
| A2A | `/a2a`; `GET /a2a/health`; card `GET /.well-known/agent.json` | FR-01B |
| WebUI | `/` (SPA; canonical `/dashboard`) | strict API client (FR-17) |

Ports (native split-role): API 8074 / Web 8075 / MCP 8076 / A2A 8077.

## Authentication & authorisation (FR-04, FR-05, FR-01B)
- All tool/API calls require authentication except health endpoints (`cloud_dog_idam`; API keys via
  `X-API-Key` / `Authorization: Bearer`, plus JWT). Default unresolved role → `viewer`.
- `GET /a2a/health` returns **401** without auth; `Authorization: Bearer <key>` and `X-API-Key` use the same
  validator; strict-local `TEST_A2A_API_KEY=12345678` → 200.
- RBAC: per profile / collection / tool-category; admin tools admin-only. Roles `admin`/`user`/`viewer`
  (+ legacy aliases) — `ROLES-AND-USECASES.md §1`. Resource-scoped cascade (group→collection) via the
  `cloud_dog_idam` 0.5.0 resolver — `DATA-MODEL.md §3` (activated when the image carries `cloud_dog_idam>=0.5.0`).
- Non-admin callers never receive stored secrets (central masking) — `mask_secrets` (0.5.0).

## Principal REST routes
`GET /api/v1/health`, `GET /api/v1/tools`, `POST|GET /api/v1/tools/{tool_name}`, `GET /api/auth/status`,
`GET /api/config`, `GET /api/status`, `GET /api/logs`, `GET /api/config-events`, `GET /api/audit-log`,
`POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /api-docs`. Full spec: `openapi.json`.

## MCP tool inventory (92 tools)
The **runtime registry `src/index_tools/tools/registry.py` is the single source of truth** (92 tools, unique;
`UT1_40` asserts `len(tools) == 92`; 21 are the W28E-603 `structure_*` family). FR-16A requires the
documented catalogue to match runtime exactly — reconciled to 92 by W28A-749. Tool categories:
- **ingest/index:** `ingest_text`, `ingest_upload`, `ingest_reference`, `ingest_preview`, `bulk_index`,
  `ingest_stream_{open,event,close}`, `ingest_health`
- **search/retrieve:** `search`, `search_explain`, `retrieve`, `index_list`, `collection_get`
- **lifecycle/delete:** `delete_by_id`, `delete_by_filter`, `reindex_run`, `retention_run`
- **profiles/collections/sources:** `profiles_list`, `profile_get`, `collections_list`, `list_collections`,
  `source_configs_list`, `source_config_get`, `admin_{profile,collection,source_config}_{create,update,delete}`
- **jobs:** `job_{list,get,cancel,retry,wait,stream,delete}`, `queue_status`
- **IDAM:** `users_list`, `user_get`, `groups_list`, `group_get`, `api_keys_list`, `rbac_bindings_list`,
  `admin_{user,group,api_key}_*`, `admin_rbac_{bind,unbind}` (the cascade write surface)
- **convert/parse/ocr:** `extract_only`, `ocr_run`, `parsers_list`, `parser_test`, `table_extract`,
  `backend_health_check`, `embedding_health_check`
- **files:** `file_{upload,download,get,list,delete}`
- **structure (W28E-603, 21):** `structure_corpus_*`, `structure_document_*`, `structure_template_*`,
  `structure_{extract,health,outline_get,pages_list,sections_list,link_to_vdb_records}`
- **a2a:** `a2a_config_events`

(Full per-tool params/output: `docs/archive/MCP-REFERENCE.md` + `GET /mcp/tools` live.)
