---
doc-id: WARRANTY-1.0RC01
project: index-retriever-mcp-server
generated: 2026-06-25T08:00:14Z
generator: scripts/build-warranty-table.py v1.0
standard: PS-CLOSEOUT-WARRANTY v1.0
---

# index-retriever-mcp-server — 1.0RC01 Release Warranty Table

Per PS-CLOSEOUT-WARRANTY: every row must reach `verdict=PASS` before the lane may close.
Stream-B and Stream-C closeout columns are backed by the W28E-1805B and W28E-1805C evidence packs.

## Section A — Requirements + UseCases + Test-Design coverage

| id | kind | title | since | source_evidence | design_row_present | binding_row_present | cross_surface_covered | webui_observation_bound | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `CS-001` | CS | `CS-001` \| Anon attempts data read \| `api`, `mcp`, `a2a`, `webui` \| `anon` \| | `W28E-1805A-current` | `docs:line 825` | YES | YES | YES | YES | **PASS** |
| `CS-002` | CS | `CS-002` \| read-only attempts write \| `api`, `mcp` \| `read-only` \| `403` \|  | `W28E-1805A-current` | `docs:line 826` | YES | YES | YES | YES | **PASS** |
| `CS-003` | CS | `CS-003` \| Missing required param \| `api` \| `admin` \| `422` \| `T-UT-031` | `W28E-1805A-current` | `docs:line 827` | YES | YES | YES | N-A | **PASS** |
| `CS-004` | CS | `CS-004` \| Wrong-role privileged op \| `mcp` \| `read-write` \| `403` \| `T-UT- | `W28E-1805A-current` | `docs:line 828` | YES | YES | YES | N-A | **PASS** |
| `CS-005` | CS | `CS-005` \| Anonymous caller attempts protected API operation. \| `api` \| `anon | `W28E-1805A-current` | `docs:line 838` | YES | YES | YES | N-A | **PASS** |
| `CS-006` | CS | `CS-006` \| Anonymous caller attempts protected MCP operation. \| `mcp` \| `anon | `W28E-1805A-current` | `docs:line 839` | YES | YES | YES | N-A | **PASS** |
| `CS-007` | CS | `CS-007` \| Anonymous caller attempts protected A2A operation. \| `a2a` \| `anon | `W28E-1805A-current` | `docs:line 840` | YES | YES | YES | N-A | **PASS** |
| `CS-008` | CS | `CS-008` \| Read-only caller attempts protected API write/admin action. \| `api` | `W28E-1805A-current` | `docs:line 841` | YES | YES | YES | N-A | **PASS** |
| `CS-009` | CS | `CS-009` \| Read-only caller attempts protected MCP write/admin action. \| `mcp` | `W28E-1805A-current` | `docs:line 842` | YES | YES | YES | N-A | **PASS** |
| `CS-010` | CS | `CS-010` \| Read-only caller attempts protected A2A write/admin action. \| `a2a` | `W28E-1805A-current` | `docs:line 843` | YES | YES | YES | N-A | **PASS** |
| `CS-011` | CS | `CS-011` \| API request misses a required parameter and receives structured vali | `W28E-1805A-current` | `docs:line 844` | YES | YES | YES | N-A | **PASS** |
| `CS-012` | CS | `CS-012` \| MCP request misses a required parameter and receives structured vali | `W28E-1805A-current` | `docs:line 845` | YES | YES | YES | N-A | **PASS** |
| `CS-013` | CS | `CS-013` \| A2A request misses a required parameter and receives structured vali | `W28E-1805A-current` | `docs:line 846` | YES | YES | YES | N-A | **PASS** |
| `FR-001` | FR | `FR-001` \| Expose the API, MCP, A2A, and WebUI interfaces with health, route-pr | `W28E-1805A-current` | `docs:line 133` | YES | YES | YES | YES | **PASS** |
| `FR-002` | FR | `FR-002` \| Preserve core pipeline, configuration, bootstrap, audit, metadata, c | `W28E-1805A-current` | `docs:line 134` | YES | YES | YES | N-A | **PASS** |
| `FR-003` | FR | `FR-003` \| Provide backend contract parity and service branch coverage for VDB, | `W28E-1805A-current` | `docs:line 135` | YES | YES | YES | N-A | **PASS** |
| `FR-004` | FR | `FR-004` \| Execute application and WebUI workflows for upload, search, retrieve | `W28E-1805A-current` | `docs:line 136` | YES | YES | YES | YES | **PASS** |
| `FR-005` | FR | `FR-005` \| Maintain system-level runtime, migration, cleanup, logging, and oper | `W28E-1805A-current` | `docs:line 137` | YES | YES | YES | N-A | **PASS** |
| `FR-006` | FR | `FR-006` \| Preserve parser-tier ingest/search performance baselines and parser  | `W28E-1805A-current` | `docs:line 138` | YES | YES | YES | N-A | **PASS** |
| `FR-007` | FR | `FR-007` \| Prove integration-tier backend, parser, metadata, job, OpenAPI, and  | `W28E-1805A-current` | `docs:line 139` | YES | YES | YES | N-A | **PASS** |
| `FR-008` | FR | `FR-008` \| Maintain security and rules-compliance coverage over authentication, | `W28E-1805A-current` | `docs:line 140` | YES | YES | YES | YES | **PASS** |
| `FR-009` | FR | `FR-009` \| Support conversion, parsing, OCR, table extraction, source extractio | `W28E-1805A-current` | `docs:line 141` | YES | YES | YES | N-A | **PASS** |
| `FR-010` | FR | `FR-010` \| Apply configured chunking and canonical metadata enrichment consiste | `W28E-1805A-current` | `docs:line 142` | YES | YES | YES | N-A | **PASS** |
| `FR-011` | FR | `FR-011` \| Detect duplicates using configured hash/size/mtime policy and record | `W28E-1805A-current` | `docs:line 143` | YES | YES | YES | N-A | **PASS** |
| `FR-012` | FR | `FR-012` \| Route embedding-provider selection and embedding dimension validatio | `W28E-1805A-current` | `docs:line 144` | YES | YES | YES | N-A | **PASS** |
| `FR-013` | FR | `FR-013` \| Route vector backend operations, provider diagnostics, parser/OCR/ta | `W28E-1805A-current` | `docs:line 145` | YES | YES | YES | N-A | **PASS** |
| `FR-014` | FR | `FR-014` \| Return stable search and retrieval output with inline content, sourc | `W28E-1805A-current` | `docs:line 146` | YES | YES | YES | YES | **PASS** |
| `FR-015` | FR | `FR-015` \| Support stateful and streaming ingestion sessions with ordering keys | `W28E-1805A-current` | `docs:line 147` | YES | YES | YES | N-A | **PASS** |
| `FR-016` | FR | `FR-016` \| Keep the complete MCP tool inventory documented and matching runtime | `W28E-1805A-current` | `docs:line 148` | YES | YES | YES | N-A | **PASS** |
| `FR-017` | FR | `FR-017` \| Preserve WebUI/API parity, controlled operation handling, middleware | `W28E-1805A-current` | `docs:line 149` | YES | YES | YES | YES | **PASS** |
| `FR-018` | FR | `FR-018` \| Bind the WebUI IDAM/admin route contract, including `/idam/users` an | `W28E-1805A-current` | `docs:line 150` | YES | YES | YES | YES | **PASS** |
| `NF-001` | NF | `NF-001` \| Reuse required platform packages for configuration, logging, API, ID | `W28E-1805A-current` | `docs:line 547` | YES | YES | N-A | N-A | **PASS** |
| `NF-002` | NF | `NF-002` \| Keep configuration, logging, audit, Vault, and secret hygiene enforc | `W28E-1805A-current` | `docs:line 548` | YES | YES | N-A | N-A | **PASS** |
| `NF-003` | NF | `NF-003` \| Preserve engineering discipline: no direct environment fallback chai | `W28E-1805A-current` | `docs:line 549` | YES | YES | N-A | N-A | **PASS** |
| `NF-004` | NF | `NF-004` \| Maintain documentation, requirement, use-case, test-design, scope-ma | `W28E-1805A-current` | `docs:line 550` | YES | YES | N-A | N-A | **PASS** |
| `UC-001` | UC | `UC-001` \| Upload/index/query content in a profile collection. \| `user`, `view | `W28E-1805A-current` | `docs:line 93` | YES | YES | YES | YES | **PASS** |
| `UC-002` | UC | `UC-002` \| Index remote references and source extraction outputs. \| `user`, `a | `W28E-1805A-current` | `docs:line 94` | YES | YES | YES | N-A | **PASS** |
| `UC-003` | UC | `UC-003` \| Stream event content into an ordered ingest session. \| `user` \| `F | `W28E-1805A-current` | `docs:line 95` | YES | YES | YES | N-A | **PASS** |
| `UC-004` | UC | `UC-004` \| Detect duplicate uploads and apply configured dedupe policy. \| `use | `W28E-1805A-current` | `docs:line 96` | YES | YES | YES | N-A | **PASS** |
| `UC-005` | UC | `UC-005` \| Administer profiles, collections, tools, jobs, and backend health. \ | `W28E-1805A-current` | `docs:line 97` | YES | YES | YES | YES | **PASS** |
| `UC-006` | UC | `UC-006` \| Run retention, delete, reindex, and cleanup operations with audit. \ | `W28E-1805A-current` | `docs:line 98` | YES | YES | YES | YES | **PASS** |
| `UC-007` | UC | `UC-007` \| Operate IDAM users/groups/API keys/RBAC and route users through cano | `W28E-1805A-current` | `docs:line 99` | YES | YES | YES | YES | **PASS** |

## Section B — Functional delivery coverage

| id | impl_committed | unit_test | integration_test | acceptance_test | surface_api | surface_mcp | surface_a2a | idam_role_negative | audit_event_emitted | ajobs_integration | preprod_deployed | preprod_smoke | sibling_regression | variation_pinned | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `FR-001` | YES (src/index_server/mcp_server.py:1235) | PASS | N-A | N-A | PASS | PASS | PASS | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-002` | YES (src/index_tools/bootstrap.py:278) | PASS | N-A | N-A | N-A | PASS | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-003` | YES (src/index_tools/tools/service.py:3259) | PASS | N-A | N-A | N-A | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-004` | YES (src/index_server/mcp_server.py:532) | N-A | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-005` | YES (src/index_server/logging_runtime.py:78) | N-A | PASS | N-A | PASS | N-A | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-006` | YES (src/index_tools/tools/service.py:3284) | PASS | N-A | N-A | N-A | N-A | N-A | N-A | N-A | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-007` | YES (src/index_server/api_server.py:1380) | N-A | PASS | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-008` | YES (src/index_server/auth/middleware.py:89) | PASS | PASS | N-A | PASS | PASS | PASS | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-009` | YES (src/index_tools/tools/service.py:4103) | PASS | PASS | PASS | PASS | PASS | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-010` | YES (src/index_tools/pipeline/metadata.py:80) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-011` | YES (src/index_tools/pipeline/dedupe.py:55) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-012` | YES (src/index_tools/embeddings/adapter.py:36) | PASS | N-A | PASS | N-A | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-013` | YES (src/index_tools/tools/service.py:978) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-014` | YES (src/index_tools/tools/service.py:3285) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-015` | YES (src/index_tools/tools/service.py:4240) | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-016` | YES (src/index_tools/tools/registry.py:92) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |
| `FR-017` | YES (src/index_server/web_server.py:148) | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FR-018` | YES (src/index_server/web_server.py:570) | PASS | N-A | N-A | PASS | N-A | N-A | PASS | PASS | N-A | PASS | PASS | PASS | PASS | **PASS** |

## Section C — WebUI + E2E coverage

W28E-1805C Stream-C coverage is consolidated through the full local Docker WebUI/E2E run, route inventory, IDAM/RBAC negative tests, a11y checks, MCP/A2A console tests, jobs/lifecycle tests, and preprod closeout evidence under `working/evidence/W28E-1805C/current/`.

| page | role | uc_id | playwright_spec | screenshot | axe_a11y | style_conformance | url_canonical | positive_assertion | negative_assertion | webui_observation_closed | preprod_url_smoke | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Login | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Login | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Login | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Login | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Top-Menu | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Top-Menu | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Top-Menu | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Top-Menu | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Left-Menu | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Left-Menu | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Left-Menu | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Left-Menu | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Footer | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Footer | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Footer | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Footer | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Audit-Log | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Audit-Log | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Audit-Log | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Audit-Log | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Users | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Users | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Users | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Users | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Groups | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Groups | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Groups | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Groups | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-API-Keys | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-API-Keys | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-API-Keys | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-API-Keys | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Roles | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Roles | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Roles | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-Roles | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-RBAC | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-RBAC | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-RBAC | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Admin-RBAC | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-API-Docs | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-API-Docs | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-API-Docs | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-API-Docs | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-MCP-Console | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-MCP-Console | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-MCP-Console | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-MCP-Console | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-A2A-Console | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-A2A-Console | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-A2A-Console | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| Developer-A2A-Console | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Jobs | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Jobs | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Jobs | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Jobs | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Settings | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Settings | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Settings | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-Settings | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-About | admin | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-About | read-write | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-About | read-only | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| System-About | anon | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-001` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-001` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-001` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-001` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-002` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-002` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-002` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-002` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-003` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-003` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-003` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-003` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-004` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-004` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-004` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-004` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-005` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-005` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-005` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-005` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-006` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-006` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-006` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-006` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | admin | `UC-007` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-write | `UC-007` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | read-only | `UC-007` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| (UC-row) | anon | `UC-007` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
