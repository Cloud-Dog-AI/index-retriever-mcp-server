---
template-id: T-TSS
template-version: 1.0
project: index-retriever-mcp-server
doc-last-updated: 2026-06-25T08:00:14Z
doc-git-commit: W28E-1805C-closeout
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-06-25T08:00:14Z
---

# index-retriever-mcp-server — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-06-25T08:50:39+01:00
- **Commit:** `W28E-1805C-closeout` (`main`)
- **Totals:** 76 WebUI/E2E tests | 76 passed | 0 failed | 0 skipped
- **Local Docker image:** `sha256:08a38c1ef8c13580a696cb7ed79db4dbd5a468cf1e690d99b59d3e3b7d691d7e`
- **Raw evidence:** `working/evidence/W28E-1805C/current/logs/local-docker-webui-playwright-search-backfill-full-clean.log`

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_a2a_run_server_uses_env` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_admin_collection_create_endpoint` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_api_app_base_path_env_override_retains_legacy_compat` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_api_app_routes_cover_auth_and_errors` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_api_create_runtime_app_typeerror_fallback` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_api_run_server_uses_env` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_build_log_payload_synthesises_blank_messages` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_build_status_payload_counts_active_documents_from_runtime` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_entrypoint_and_streaming_wrappers` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_mcp_app_and_execute_tool_paths` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_mcp_build_app_typeerror_fallback` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_mcp_run_server_uses_env` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_read_jsonl_records_many_includes_rotated_siblings` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_requires_caller_auth_locks_identity_bearing_paths` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_web_run_server_uses_env` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_web_runtime_config_and_spa_admin_routes` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_31.test_ut1_31_server_runtime_paths::test_web_tool_proxy_cookie_role_gates_service_key` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_42.test_ut1_42_connector_gdrive::test_connector_gdrive_error_mapping` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_42.test_ut1_42_connector_gdrive::test_connector_gdrive_resolve_query_link` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_42.test_ut1_42_connector_gdrive::test_connector_gdrive_resolve_raw_id` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_42.test_ut1_42_connector_gdrive::test_connector_gdrive_resolve_requires_file_id` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |
| `tests.unit.UT1_42.test_ut1_42_connector_gdrive::test_connector_gdrive_resolve_shared_link` | UT/ST/IT | pass | 2026-06-17 | `722fe3ec` | |

## 3. Failures (detail)

_None._

## 4. W28E-1805C Closeout Addendum

- Service unit regression: `tests/unit/UT1_34/test_ut1_34_service_and_adapter_branches.py::test_service_search_backfills_local_matches_when_vdb_returns_partial` passed.
- WebUI/API state regression: `tests/unit/UT1_31/test_ut1_31_server_runtime_paths.py::test_web_tool_proxy_cookie_role_gates_api_forward` passed.
- Local Docker readiness: `document_count=0`, API/auth/Web/MCP/A2A all returned `200` before full E2E.
- Full browser E2E: 76/76 passed against the rebuilt local image.
