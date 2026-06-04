# W28E-603 Phase 1 — Reference-First Design Map (CIC §3)

Phase 1 = design brief §24 "Model And Persistence Foundation": canonical structure model, `cloud_dog_db`
persistence integration, migrations, basic CRUD APIs, basic MCP listing/get tools, backend-matrix smoke tests.
Everything mirrors **validated existing in-repo patterns** (CIC §8); no bespoke replacements (RULES §1.4).

## Canonical patterns this phase mirrors (side-by-side)

| Concern | Existing canonical pattern (reference) | Phase-1 reuse |
|---|---|---|
| ORM model base | `src/index_tools/db/models.py:24` `IndexPlatformDbState(PlatformBase, TimestampMixin)` | New rows extend the same `cloud_dog_db.PlatformBase` + `TimestampMixin` |
| Engine/session | `src/index_tools/db/runtime.py:209` `initialise_database()` → `runtime.session_manager.session()` | Repository uses the same cached runtime + sync session context manager |
| Migrations | Alembic in `database/migrations/cloud_dog_db/versions/`; head `20260305_0001` (`down_revision=None`) | New `20260604_0002_structure_foundation` chains off `20260305_0001` |
| DB dialect selection | `runtime.py:133` env `CLOUD_DOG_DB__DIALECT` / `*_DB__URL` (sqlite default; postgres/mysql) | Backend matrix legs reuse the same env knobs |
| Tool registry | `src/index_tools/tools/registry.py:48` `ToolSpec`; `build_default_tool_registry():88` | New `ToolSpec`s appended; same schema-first registry (brief §13 MCP req) |
| Pydantic I/O models | `src/index_tools/tools/definitions.py` (pydantic v2 `BaseModel`) | New structure request/response models added here |
| MCP dispatch | `src/index_server/mcp_server.py:419` `execute_tool()` if/elif → `service.<m>()`; perms `_required_permission_for_tool():194` | New `if tool_name == "structure_..."` cases + permission rows |
| API routes | `src/index_server/api_server.py:793` `build_api_app()`; nested handlers + `app.<verb>(path)(handler)` @1909; auth `_auth_or_raise`/`_require_or_raise` | New nested structure handlers + registrations under `/api/v1/structure/*` |
| Service handle | Transport layers hold `IndexService` (`active_service` / `execute_tool(service,…)`) | Lazy `IndexService.structure` property → self-contained `StructureService` |
| Audit | `IndexService.audit_logger` (`AuditLogger.log_admin_action(...)`, `logger.py:174`) | Structure create/delete audited via `log_admin_action(action=…, target_type="structure_document")` |

## New code (Phase 1 scope only)

```
src/index_tools/structure/
  __init__.py        # exports: SCHEMA_VERSION, models, StructureService
  ids.py             # deterministic IDs (brief §8.2): sha256 over canonical tuples
  models.py          # canonical pydantic models (brief §6.1-6.8) + enums + SCHEMA_VERSION
  repository.py      # cloud_dog_db-routed persistence (sync session); CRUD + child listing
  service.py         # StructureService: transport-neutral create/get/list/delete/outline/pages/...
src/index_tools/db/structure_models.py   # 9 ORM tables (PlatformBase+TimestampMixin), JSON payload columns
database/migrations/cloud_dog_db/versions/20260604_0002_structure_foundation.py
```

### Logical resources persisted (brief §5.2 / §6)
`structure_documents` (parent) + child tables `structure_pages`, `structure_blocks`, `structure_sections`,
`structure_styles`, `structure_tables`, `structure_figures`, `structure_relations`, `structure_extractor_runs`.
Each child carries first-class identity/link/order columns + a JSON `payload` for the full canonical object
(§3 permits JSON behind the SQL interface). VDB search-view generation is **out of Phase 1** (Phase 3).

### Deterministic IDs (brief §8.2)
```
structure_document_id = sha256(profile_id, collection_id, source_hash, parser_family, schema_version)
page_id               = sha256(structure_document_id, page_number)
block_id              = sha256(page_id, reading_order_index, bbox, text_hash, block_type)
section_id            = sha256(structure_document_id, normalised_path, start_page, title_hash)
```
Local helper standardised in `structure/ids.py` (no incompatible local identity scheme — §8.2).

### Phase-1 API surface (brief §12, separate from /search,/retrieve,/ingest)
- `POST   /api/v1/structure/documents`              create canonical structure document (+children)
- `GET    /api/v1/structure/documents`              list (profile/collection filter, pagination)
- `GET    /api/v1/structure/documents/{id}`         get (with `include` for children)
- `DELETE /api/v1/structure/documents/{id}`         delete (audited)
- `GET    /api/v1/structure/documents/{id}/outline` section hierarchy
- `GET    /api/v1/structure/documents/{id}/pages`   list pages
- `GET    /api/v1/structure/health`                 structure subsystem health (db probe)

### Phase-1 MCP tools (brief §13 canonical names)
`structure_health`, `structure_document_create`, `structure_document_get`, `structure_document_list`,
`structure_document_delete`, `structure_outline_get`, `structure_pages_list`, `structure_sections_list`.
Registered through the same `ToolSpec` registry; RBAC: read→`collection.read`, write/delete→`collection.write`.

### Tests
- `tests/unit/UT_W28E603_Structure/` — model + deterministic-id + repository CRUD + service round-trip (sqlite).
- `tests/system/ST_W28E603_StructureBackendMatrix/` — parametrized `["sqlite","postgresql","mysql"]`, postgres/mysql
  **skip** when unconfigured (mirrors existing VDB-matrix skip pattern, `tests/w23a_helpers.py`).
- Regression gate: `python -m pytest tests/unit --env tests/env-UT -q` must remain green.

## Out of Phase 1 (later phases — NOT built here)
Provider/parser normalisation (MinerU/Marker/Docling) §9 → Phase 2; VDB search views §7.3 → Phase 3;
corpus analysis §10 → Phase 4; templates §11 → Phase 5; db-mcp exposure §16 + full backend matrix → Phase 6.
A2A skills (§14) and WebUI (§15) for structure are deferred to their phases. Object-storage artefacts (§7.2) deferred.
