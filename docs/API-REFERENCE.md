---
template-id: T-API
template-version: 1.0
applies-to: docs/API-REFERENCE.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-12
doc-git-commit: 5cba8eb76245a4d7ba5af6f0b3b765199a6f6ee6
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# index-retriever-mcp-server — API-REFERENCE

> **Template version:** T-API v1.0 — REST surface authoritative reference. `openapi.json` is build-generated; this doc explains it.

## 1. Auth model
Auth modes accepted (`api_key`, `cookie`, `vault-bootstrap`), header name, RBAC mapping.

## 2. Routes

**You MUST include:** every route registered by the service. Group by section: Auth / Admin / Data / Health.

| Method | Path | Auth | RBAC | Summary | Request | Response |
|---|---|---|---|---|---|---|
| GET | `/health` | none | n/a | liveness | — | `{status:"ok"}` |

## 3. Error model
Standard error envelope, status codes, retryability.

## 4. Examples
**You MUST include:** at least one worked curl example per route group.

```
curl -H "X-API-Key: ${API_KEY}" https://<host>/api/v1/<route>
```

## 5. Cross-references
- [openapi.json](openapi.json)
- [MCP-REFERENCE.md](MCP-REFERENCE.md)
- [A2A-REFERENCE.md](A2A-REFERENCE.md)
- [WEBUI-REFERENCE.md](WEBUI-REFERENCE.md)
- PS-20-api.md

## 6. Project-specific notes



<!-- W28C-1710a recovery: full content from archive/2026-06-12/API.md (archived sha256=e5e1750394d0, 52 lines) -->

## Recovered domain content — `archive/2026-06-12/API.md` (52 lines)

_This section carries forward the full content of the archived predecessor doc verbatim. Topic checklist + SHA256 chain in `cloud-dog-ai-platform-standards/working/evidence/W28C-1710a/per-doc/index-retriever-mcp-server/API.md.topics.tsv`. Archive contents are unchanged (sha256 stable)._

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

## MCP tool inventory (94 tools)
The **runtime registry `src/index_tools/tools/registry.py` is the single source of truth** (94 tools, unique;
`UT1_40` asserts `len(tools) == 94`; 22 are the W28E-603/W28M-1603D `structure_*` family and one is the
W28D-440E5 `hdro_extract` source extractor). FR-16A requires the
documented catalogue to match runtime exactly — reconciled to 94 by W28M-1603D. Tool categories:
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
- **structure (W28E-603/W28M-1603D, 22):** `structure_corpus_*`, `structure_document_*`, `structure_template_*`,
  `structure_{extract,health,outline_get,pages_list,sections_list,link_to_vdb_records}`
- **a2a:** `a2a_config_events`

(Full per-tool params/output: `docs/archive/MCP-REFERENCE.md` + `GET /mcp/tools` live.)
