---
template-id: T-TST
template-version: 1.1
applies-to: docs/TESTS.md
project: index-retriever-mcp-server
doc-last-updated: 2026-06-12T16:37:04Z
doc-git-commit: 167f371208d2dbe673d692b181cfb25f78d51cb9
doc-git-branch: w28a-749-idam
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T16:37:04Z
req-trace-version: 1.0
total-tests: 0
coverage-percent: 0
---

# Tests

## Service Scope
Ingestion, parser orchestration, OCR/table handling, indexing, search, retrieval, and queue-backed maintenance for enterprise content.

## Test Inventory
| Tier | Present | Tests | Last Run (W28A-964) |
|------|---------|-------|---------------------|
| `quality` | Yes | 47 | 47 passed, 0 failed |
| `unit` | Yes | 137 | 137 passed, 0 failed |
| `system` | Yes | 25 | 25 passed, 0 failed |
| `integration` | Yes | 46 | 46 passed, 0 failed |
| `application` | Yes | 24 | 24 passed, 0 failed |
| `contract` | Yes | 4 | — |
| `parser` | Yes | 3 | — |
| `security` | Yes | 6 | — |
| **Playwright** | Yes | 54 | 54 passed, 0 failed |
| **Total** | — | **346** | **333 passed (QT+UT+ST+IT+AT+PW)** |

## Current Evidence Model
- The repository keeps execution evidence in repo-local working reports and rerunnable pytest suites.
- Before release, rerun the relevant `QT`, `UT`, `ST`, `IT`, and `AT` tiers against the intended environment overlays.
- This document records the current catalogue rather than claiming a release verdict.

## Standard Commands
```bash
python3 -m pytest tests/quality --env tests/env-QT -q
python3 -m pytest tests/unit --env tests/env-UT -q
python3 -m pytest tests/system --env tests/env-ST -q
python3 -m pytest tests/integration --env tests/env-IT -q
python3 -m pytest tests/application --env tests/env-AT -q
```

## Notes
- Top-level test directories present: `__pycache__`, `application`, `contract`, `integration`, `parser`, `quality`, `security`, `system`, `unit`.
- Environment overlays and private credentials are intentionally not published in this document set.

## W28A-513 Added Coverage

### ST1.15 E2E gap coverage
- File: `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py`
- Purpose:
  - verify all documented chunking strategies against a real VDB-backed ingest path,
  - verify a real OCR provider path (`local` / Tesseract),
  - verify the actual retrieval output contract (inline content plus source URI traceability).
- Requirements covered:
  - `FR-09A`
  - `FR-10A`
  - `FR-14A`

### UT1.40 tool registry completeness
- File: `tests/unit/UT1_40/test_ut1_40_tool_registry.py`
- Purpose:
  - enforce the exact runtime tool inventory count (`90`),
  - ensure names are unique and the registry contract remains stable.
- Requirements covered:
  - `FR-16A`

## Traceability Matrix

| Requirement | Test File | Test Function/Class | Status |
|---|---|---|---|
| FR-01 (Interfaces: MCP + HTTP + WebUI) | `tests/integration/IT1_1/test_it1_1.py` | `test_api_health_endpoint` | COVERED |
| FR-01B (A2A auth contract parity) | `tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py` | `test_a2a_api_key_validation_parity`, `test_a2a_api_key_invalid_rejected`, `test_auth_middleware_refreshes_provider_after_runtime_key_update` | COVERED |
| FR-01B (A2A auth contract parity) | `tests/integration/IT1_18/test_it1_18_a2a_health_auth_matrix.py` | `test_a2a_health_auth_matrix` | COVERED |
| FR-02 (Config precedence) | `tests/unit/UT1_1/test_ut1_1_config_loader_precedence.py` | `test_config_loader_precedence` | COVERED |
| FR-02 (Config validation) | `tests/unit/UT1_3/test_ut1_3_config_validation.py` | UT1_3 suite | COVERED |
| FR-03 (Multi-profile support) | `tests/unit/UT1_4/test_ut1_4_profile_model_validation.py` | `test_profile_model_validation` | COVERED |
| FR-03 (Multi-profile support) | `tests/system/ST1_1/test_st1_1.py` | `test_profile_create_persist` | COVERED |
| FR-04 (Authentication) | `tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py` | `test_api_key_env_mapping_parses_roles_and_skips_empty` | COVERED |
| FR-05 (RBAC) | `tests/unit/UT1_5/test_ut1_5_rbac_policy_eval.py` | `test_rbac_policy_eval` | COVERED |
| FR-05 (RBAC) | `tests/integration/IT1_21/test_it1_21_collection_rbac.py` | `test_collection_level_rbac_enforced` | COVERED |
| FR-06 (Audit logging) | `tests/unit/UT1_7/test_ut1_7_audit_event_shape.py` | `test_audit_event_shape` | COVERED |
| FR-06 (Audit redaction) | `tests/unit/UT1_8/test_ut1_8_audit_redaction.py` | UT1_8 suite | COVERED |
| FR-07 (Job / queue management) | `tests/unit/UT1_27/test_ut1_27_job_model_validation.py` | `test_job_model_validation` | COVERED |
| FR-07 (Job / queue management) | `tests/unit/UT1_46_JobLifecycleSimulation/test_job_lifecycle.py` | UT1_46 suite | COVERED |
| FR-07 (Job management tools) | `tests/integration/IT1_20/test_it1_20_job_management_tools.py` | IT1_20 suite | COVERED |
| FR-08 (Ingestion inputs) | `tests/application/AT1_1/test_at1_1.py` | `test_full_workflow_upload_search_retrieve` | COVERED |
| FR-09 (Conversion and parsing) | `tests/unit/UT1_12/test_ut1_12_convert_registry_selection.py` | `test_convert_registry_selection` | COVERED |
| FR-09 (Conversion and parsing) | `tests/unit/UT1_13/test_ut1_13_convert_pdf_extract.py` | UT1_13 suite | COVERED |
| FR-09 (Conversion and parsing) | `tests/unit/UT1_14/test_ut1_14_convert_office_extract.py` | UT1_14 suite | COVERED |
| FR-09A (OCR provider support) | `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py` | `test_st_15_local_ocr_provider_extracts_non_empty_text` | COVERED |
| FR-10 (Chunking and metadata) | `tests/unit/UT1_15/test_ut1_15_chunking_token_strategy.py` | `test_chunking_token_strategy` | COVERED |
| FR-10 (Chunking overlap) | `tests/unit/UT1_16/test_ut1_16_chunking_overlap.py` | UT1_16 suite | COVERED |
| FR-10 (Metadata enrichment) | `tests/unit/UT1_17/test_ut1_17_metadata_enrichment.py` | UT1_17 suite | COVERED |
| FR-10A (Chunking strategy matrix) | `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py` | `test_st_15_chunking_strategies_ingest_expected_boundaries` | COVERED |
| FR-10B (Canonical metadata) | `tests/unit/UT1_47/test_ut1_47_core_metadata.py` | UT1_47 suite | COVERED |
| FR-10B (Canonical metadata) | `tests/integration/IT1_23/test_it1_23_core_metadata.py` | IT1_23 suite | COVERED |
| FR-11 (Deduplication hash) | `tests/unit/UT1_18/test_ut1_18_dedupe_hash_detection.py` | `test_dedupe_hash_detection` | COVERED |
| FR-11 (Deduplication size+mtime) | `tests/unit/UT1_19/test_ut1_19_dedupe_size_mtime_detection.py` | UT1_19 suite | COVERED |
| FR-11 (Dedupe policy skip) | `tests/unit/UT1_20/test_ut1_20_dedupe_policy_skip.py` | UT1_20 suite | COVERED |
| FR-11 (Dedupe policy replace) | `tests/unit/UT1_21/test_ut1_21_dedupe_policy_replace.py` | UT1_21 suite | COVERED |
| FR-11 (Dedupe policy version) | `tests/unit/UT1_22/test_ut1_22_dedupe_policy_version.py` | UT1_22 suite | COVERED |
| FR-12 (Embedding providers) | `tests/unit/UT1_23/test_ut1_23_embedding_registry_lookup.py` | UT1_23 suite | COVERED |
| FR-12 (Embedding dimension) | `tests/unit/UT1_43/test_ut1_43_embedding_dimension_validation.py` | UT1_43 suite | COVERED |
| FR-13 (Vector backends - Chroma) | `tests/integration/IT2_1/test_it2_1_chroma_contract.py` | IT2_1 suite | COVERED |
| FR-13 (Vector backends - Qdrant) | `tests/integration/IT2_2/test_it2_2_qdrant_contract.py` | IT2_2 suite | COVERED |
| FR-13 (Vector backends - OpenSearch) | `tests/integration/IT2_3/test_it2_3_opensearch_contract.py` | IT2_3 suite | COVERED |
| FR-13 (Vector backends - PGVector) | `tests/integration/IT2_4/test_it2_4_pgvector_contract.py` | IT2_4 suite | COVERED |
| FR-13 (Vector backends - Weaviate) | `tests/integration/IT2_5/test_it2_5_weaviate_contract.py` | IT2_5 suite | COVERED |
| FR-13 (Vector backends - Infinity) | `tests/integration/IT2_6/test_it2_6_infinity_contract.py` | IT2_6 suite | COVERED |
| FR-14 (Search and retrieval) | `tests/unit/UT1_25/test_ut1_25_search_query_normalisation.py` | `test_search_query_normalisation` | COVERED |
| FR-14 (Search filter validation) | `tests/unit/UT1_26/test_ut1_26_search_filter_validation.py` | UT1_26 suite | COVERED |
| FR-14A (Retrieval output contract) | `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py` | `test_st_15_retrieval_returns_content_and_source_uri_traceability` | COVERED |
| FR-16 (Management operations) | `tests/unit/UT1_44/test_ut1_44_admin_config_crud.py` | `test_service_admin_config_crud_and_mcp_parity` | COVERED |
| FR-16 (Management operations) | `tests/integration/IT1_22/test_it1_22_admin_rest_config_crud.py` | `test_admin_rest_profile_user_group_api_key_lifecycle`, `test_admin_rest_rejects_non_admin_mutation` | COVERED |
| FR-16A (Tool inventory contract) | `tests/unit/UT1_40/test_ut1_40_tool_registry.py` | UT1_40 suite (90-tool count enforcement) | COVERED |
| R-VDB-01 (All 6 adapters) | `tests/integration/IT2_1/` through `tests/integration/IT2_6/` | IT2_1..IT2_6 suites | COVERED |
| R-VDB-02 (CRUD/search parity) | `tests/contract/CT1_3/test_ct1_3_backend_parity.py` | CT1_3 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_7/test_it2_7_deepdoc_parser.py` | IT2_7 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_8/test_it2_8_docling_parser.py` | IT2_8 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_9/test_it2_9_mineru_parser.py` | IT2_9 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_10/test_it2_10_marker_parser.py` | IT2_10 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_11/test_it2_11_transformers_parser.py` | IT2_11 suite | COVERED |
| R-PARSE-01 (Parser provider matrix) | `tests/integration/IT2_12/test_it2_12_internal_parser.py` | IT2_12 suite | COVERED |
| R-CONSIST-01 (Cross-backend consistency) | `tests/application/AT2_1/test_at2_1_multi_backend_consistency_chroma_qdrant.py` | AT2_1 suite | COVERED |
| R-CONSIST-01 (Cross-backend consistency) | `tests/application/AT2_2/test_at2_2_multi_backend_consistency_pgvector_opensearch.py` | AT2_2 suite | COVERED |
| R-EMBED-02 (Embedding dimension validation) | `tests/unit/UT1_43/test_ut1_43_embedding_dimension_validation.py` | UT1_43 suite | COVERED |
| R-EMBED-04 (Multi-model live test) | `tests/application/AT2_4/test_at2_4_multi_embedding_models.py` | AT2_4 suite | COVERED |
| R-DB-01 (DB access abstraction) | `tests/unit/UT1_40/test_ut1_40_database_abstraction.py` | `test_ut_db_01_engine_factory_creates_sqlite_engine` | COVERED |
| R-DB-03 (Session management) | `tests/unit/UT1_40/test_ut1_40_database_abstraction.py` | `test_ut_db_02_session_manager_roundtrip` | COVERED |
| R-DB-04 (Migration runner) | `tests/system/ST1_14/test_st1_14_database_migration.py` | ST1_14 suite | COVERED |
| R-DB-08 (Multi-dialect versioning) | `tests/system/ST1_14/test_st1_14_database_migration_multibackend.py` | ST1_14 multibackend suite | COVERED |
| R-DB-04 (Jobs migration) | `tests/unit/UT1_45/test_ut1_45_jobs_migration.py` | UT1_45 suite | COVERED |
| FR-17 (WebUI/API parity) | `tests/application/AT_WEBUI_AuthDashboard/test_webui_auth_dashboard.py` | AT_WEBUI_AuthDashboard suite | COVERED |
| FR-17 (WebUI Collection CRUD) | `tests/application/AT_WEBUI_CollectionCrud/test_webui_collection_crud.py` | AT_WEBUI_CollectionCrud suite | COVERED |
| FR-17 (WebUI File Upload) | `tests/application/AT_WEBUI_FileUpload/test_webui_file_upload.py` | AT_WEBUI_FileUpload suite | COVERED |
| FR-17 (WebUI Security Admin) | `tests/application/AT_WEBUI_SecurityAdmin/test_webui_security_admin.py` | AT_WEBUI_SecurityAdmin suite | COVERED |
| FR-15 (Streaming ingestion) | `tests/integration/IT1_12/test_it1_12.py` | `test_streaming_ingest_sse` | COVERED |
| FR-P002 (Search Explain) | `tests/unit/UT1_37/test_ut1_37_mcp_vdb041_dispatch.py`, `tests/integration/IT1_7/test_it1_7.py` | `test_execute_tool_search_explain_returns_plan_and_scoring_metadata`, `test_mcp_tool_execution` | COVERED |

## Access-control matrix (T0–T3) — IDAM b-method (W28A-749)

Suites placed under `tests/smoke/access_control_matrix_smoke.py` (T0–T2 backend) and
`tests/e2e/access-control-webui.spec.ts` (WebUI). Full matrix: `ROLES-AND-USECASES.md §3`. The cascade row
(`T3-IR-CASCADE`) + resource-scoped enforcement activate only when the deployed image carries
`cloud_dog_idam==0.5.0` (W28A-749 keystone gate); on 0.4.x the role-based tiers (T0–T2) still run.

| Tier | IDs (representative) | Proves |
|---|---|---|
| T0 smoke | `T0-IR-LIFECYCLE`, `T0-IR-INGEST`, `T0-IR-SEARCH`, `T0-IR-SCOPE-DENY`, `T0-IR-TOOLS-COUNT`(==92), `T0-IR-WEBUI-PAGES` | works, no 404, tool inventory == runtime |
| T1 common-IDAM | `T1-IR-AUTH-401`, `T1-IR-A2A-401`, `T1-IR-WEBUI-401-LOGOUT`, `T1-IR-BASELINE-USER`, `T1-IR-AUDIT-COVERAGE` | anon→401 per surface; baseline user; audit |
| T2 RBAC-by-role | `T2-IR-ADMINONLY`, `T2-IR-COLLECTION-RBAC`, `T2-IR-NOSECRET`, `T2-IR-PROXY-FORWARD`, `T2-IR-SERVICE-SCOPE`, `T2-IR-JOBS-RBAC` | role gating; no secret to non-admin; proxy forwards principal |
| T3 business + cascade | `T3-IR-UPLOAD-QUERY`, `T3-IR-REFERENCE/STREAM/DEDUPE`, `T3-IR-PROFILE-CRUD`, `T3-IR-RETENTION`, `T3-IR-SEARCH-SCOPE`, **`T3-IR-CASCADE`**, `T9-IR-PROFILE-LIVE` | UC-01..06 live; **group→collection cascade live (0.5.0-gated)** |

## 2. Coverage map

Mandatory 10-column schema per PS-REQ-TEST-TRACE v1.0 §4.2. The per-test catalogue below will be populated by operator-driven Instruction 4 work that binds @pytest.mark.req() decorators to specific REQ-IDs. Until then, all tests carry @pytest.mark.probe (KEEP-AS-PROBE disposition per PS-REQ-TEST-TRACE §7).

| Test ID | Tier | Use case | Requirement | Surface | Scenario | Variants | Env files | Known issue | Last run commit |
|---|---|---|---|---|---|---|---|---|---|


<!-- W28C-1710b design-delta additions (2026-06-14T18:01:23Z) -->

## W28C-1710b design-delta — planned tests catalogue (T-TST v1.1 10-col schema)

Per T-TST v1.1, the planned tests catalogue carries 10 columns: `test-id | tier | use-case | requirement | surface | scenario | variants | env-files | known-issue | last-run-commit`. Test binding (replacement of probe markers with `@pytest.mark.req("FR-NNN")`) is W28C-1711 work.

Consolidation rules (per W28C-1711):

1. One primary test per FR-NNN; variants via `pytest.parametrize`.
2. Common scenarios (login, RBAC matrix, anon-denied) in `tests/helpers/`.
3. Cross-surface FR uses parametrized test file; not duplicate files.
4. Every `surface: webui` FR has a Playwright test (cookie-login + RBAC matrix + screenshot + DOM-assert + console-error-gate + CW-pattern).
5. Every `surface: api|mcp|a2a` FR has a protocol-level test.
6. Every `CS-NNN` binds to `@pytest.mark.negative` test with expected denial code.
7. CRUD-applicable entities have C/R/U/D coverage.
8. Orphan retirement requires knowledge-extract worksheet.
