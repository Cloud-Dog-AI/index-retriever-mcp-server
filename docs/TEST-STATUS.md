---
template-id: T-TSS
template-version: 1.0
project: service
doc-last-updated: 2026-07-15T22:36:27.353420+00:00
doc-git-commit: f014476b8e810c83bf61e8dc957269e38dc2baaa
doc-git-branch: w28r-3016-index-retriever
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-15T22:36:27.353420+00:00
---

# service — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-07-15T22:36:27.353420+00:00
- **Commit:** `f014476b8e810c83bf61e8dc957269e38dc2baaa` (`w28r-3016-index-retriever`)
- **Runtime:** CPython 3.13.14
- **Lane:** `W28R-3016`
- **Environment:** `tests/env-ST + Vault-provided W28E603_MATRIX_POSTGRESQL_URL + W28E603_MATRIX_MYSQL_URL`
- **Command:** `.venv/bin/python -m pytest tests/system --env tests/env-ST -q`
- **Evidence:** `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-all-backends-zero-skip-junit.xml`
- **Totals:** 28 tests | 28 passed | 0 failed | 0 errors | 0 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `system.ST1_1.test_st1_1::test_profile_create_persist` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_10.test_st1_10::test_retention_cleanup` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_11.test_st1_11::test_job_enqueue_execute` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_12.test_st1_12::test_audit_log_persistence` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_13.test_st1_13_no_fallback_backend_identity::test_no_fallback_backend_identity_st` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_14.test_st1_14_database_migration::test_st_db_01_migration_upgrade_on_fresh_sqlite` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_14.test_st1_14_database_migration::test_st_db_02_crud_via_session_manager` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_14.test_st1_14_database_migration_multibackend::test_st_db_03_migration_lifecycle_upgrade_downgrade_upgrade` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_14.test_st1_14_database_migration_multibackend::test_st_db_04_schema_versioning_simulation` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_15.test_st1_15_e2e_gap_coverage::test_st_15_chunking_strategies_ingest_expected_boundaries` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_15.test_st1_15_e2e_gap_coverage::test_st_15_local_ocr_provider_extracts_non_empty_text` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_15.test_st1_15_e2e_gap_coverage::test_st_15_retrieval_returns_content_and_source_uri_traceability` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_2.test_st1_2::test_collection_create_delete` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_3.test_st1_3::test_ingest_upload_pipeline` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_4.test_st1_4::test_ingest_text_pipeline` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_5.test_st1_5::test_ingest_reference_pipeline` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_6.test_st1_6::test_search_top_k` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_7.test_st1_7::test_search_metadata_filter` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_8.test_st1_8::test_delete_by_id` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST1_9.test_st1_9::test_delete_by_filter` | ST | pass | 2026-07-15 | `f014476b` | |
| `system.ST_IntegrityVerifier.test_integrity_running::test_integrity_log_file_populated` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_IntegrityVerifier.test_integrity_running::test_integrity_record_fields` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_IntegrityVerifier.test_integrity_running::test_integrity_verifier_starts_with_server` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_LogRotation.test_rotation_config::test_rotation_handler_configured` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_LogRotation.test_rotation_config::test_rotation_parameters_from_config` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_W28E603_StructureBackendMatrix.test_st_w28e603_structure_backend_matrix::test_structure_backend_matrix_round_trip[mysql]` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_W28E603_StructureBackendMatrix.test_st_w28e603_structure_backend_matrix::test_structure_backend_matrix_round_trip[postgresql]` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |
| `system.ST_W28E603_StructureBackendMatrix.test_st_w28e603_structure_backend_matrix::test_structure_backend_matrix_round_trip[sqlite]` | UNCLASSIFIED | pass | 2026-07-15 | `f014476b` | |

## 3. Failures (detail)

_None._
