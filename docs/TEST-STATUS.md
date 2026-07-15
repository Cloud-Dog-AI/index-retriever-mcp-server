---
template-id: T-TSS
template-version: 1.0
project: index-retriever-mcp-server
doc-last-updated: 2026-07-15T21:21:01.315484Z
doc-git-commit: b74087f738679b3f1fef1744ceaadd44351e1d93
doc-git-branch: w28r-3016-index-retriever
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-15T21:21:01.315484Z
---

# index-retriever-mcp-server — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-07-15T21:21:01.315484Z
- **Commit:** `b74087f738679b3f1fef1744ceaadd44351e1d93` (`w28r-3016-index-retriever`)
- **Runtime:** CPython 3.13.14
- **Lane:** `W28R-3016`
- **Environment:** `tests/env-IT-local-docker + authorized Vault-derived environment`
- **Command:** `.venv/bin/python -m pytest tests/integration --env tests/env-IT-local-docker -q`
- **Evidence:** `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it-final-image-green.xml`
- **Totals:** 67 tests | 64 passed | 0 failed | 0 errors | 3 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `integration.IT1_1.test_it1_1::test_api_health_endpoint` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_10.test_it1_10::test_qdrant_contract_test` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_11.test_it1_11::test_embedding_provider_ollama` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_12.test_it1_12::test_streaming_ingest_sse` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_13.test_it1_13::test_source_metadata_round_trip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_14.test_it1_14::test_capability_aware_backend_planning` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_15.test_it1_15::test_infinity_adapter_contract_path` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_16.test_it1_16::test_delegation_boundary_via_cloud_dog_vdb_pipeline` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_17.test_it1_17::test_tool_catalogue_wrappers_execute` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_18.test_it1_18_a2a_health_auth_matrix::test_a2a_health_auth_matrix` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_19.test_it1_19_no_fallback_backend_identity::test_no_fallback_backend_identity_it` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_2.test_it1_2::test_api_auth_reject` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_20.test_it1_20_job_management_tools::test_job_list_lean_summary_omits_payload` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_20.test_it1_20_job_management_tools::test_job_management_tools_contract` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_21.test_it1_21_collection_rbac::test_collection_level_rbac_enforced` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_21.test_it1_21_jobs_migration::test_jobs_backend_concurrency_and_recovery` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_22.test_it1_22_admin_rest_config_crud::test_admin_rest_profile_user_group_api_key_lifecycle` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_22.test_it1_22_admin_rest_config_crud::test_admin_rest_rejects_non_admin_mutation` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_23.test_it1_23_core_metadata::test_mt2_preview_reports_parser_and_ocr_provenance` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_23.test_it1_23_core_metadata::test_mt2_text_and_upload_ingest_store_canonical_metadata` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_23.test_it1_23_core_metadata::test_mt3_filters_support_required_metadata_pack_management_fields` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_23.test_it1_23_core_metadata::test_mt3_mt4_round_trip_returns_latest_record_with_canonical_metadata` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_24.test_it1_24_openapi_contract::test_openapi_and_tool_contract_include_canonical_metadata_fields` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_25_IdamCascade.test_it1_25_idam_role_cascade::test_it1_25_baseline_roles_and_overlay_merge` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_25_IdamCascade.test_it1_25_idam_role_cascade::test_it1_25_group_collection_cascade_live_revoke` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_3.test_it1_3::test_api_auth_accept` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_4.test_it1_4::test_api_rbac_ingest_gating` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_5.test_it1_5::test_api_rbac_admin_gating` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_6.test_it1_6::test_mcp_tool_catalogue` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_7.test_it1_7::test_mcp_tool_execution` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_8.test_it1_8::test_correlation_id_propagation` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT1_9.test_it1_9::test_chroma_contract_test` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_1.test_it2_1_chroma_contract::test_it2_1_chroma_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_10.test_it2_10_marker_parser::test_it2_10_marker_parser_pdf_ir_output` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_11.test_it2_11_transformers_parser::test_it2_11_transformers_parser_pdf_ir_output` | IT | skip | 2026-07-15 | `b74087f7` | |
| `integration.IT2_12.test_it2_12_internal_parser::test_it2_12_internal_parser_pdf_ir_output` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_13.test_it2_13_ocr_provider_matrix::test_it2_13_ocr_capable_parser_matrix_extracts_text` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_14.test_it2_14_table_extraction_matrix::test_it2_14_table_extraction_returns_structured_tables` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_15_DatabaseStartup.test_it2_15_database_startup::test_it2_15_database_startup_and_crud` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_16.test_it2_16_provenance_contract::test_pdf_ocr_and_table_provenance_fields_recorded` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_16.test_it2_16_provenance_contract::test_plain_text_provenance_contract_fields` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_16.test_it2_16_provenance_contract::test_reingest_provenance_is_preserved_not_overwritten` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_2.test_it2_2_qdrant_contract::test_it2_2_qdrant_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_3.test_it2_3_opensearch_contract::test_it2_3_opensearch_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_4.test_it2_4_pgvector_contract::test_it2_4_pgvector_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_5.test_it2_5_weaviate_contract::test_it2_5_weaviate_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_6.test_it2_6_infinity_contract::test_it2_6_infinity_contract_roundtrip` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT2_7.test_it2_7_deepdoc_parser::test_it2_7_deepdoc_parser_pdf_ir_output` | IT | skip | 2026-07-15 | `b74087f7` | |
| `integration.IT2_8.test_it2_8_docling_parser::test_it2_8_docling_parser_pdf_ir_output` | IT | skip | 2026-07-15 | `b74087f7` | |
| `integration.IT2_9.test_it2_9_mineru_parser::test_it2_9_mineru_parser_pdf_ir_output` | IT | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28D440E5.test_hdro_live::test_hdro_live_vault_key_returns_hdi_gii_country_values` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E1805B_StructureGaps.test_it_w28e1805b_structure_gaps::test_extract_analyse_generate_match_end_to_end` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E1859_RbacBindingSlashRoute.test_it_w28e1859_rbac_binding_slash_route::test_webui_slash_rbac_binding_create_accepts_subject_id[/api/v1]` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E1859_RbacBindingSlashRoute.test_it_w28e1859_rbac_binding_slash_route::test_webui_slash_rbac_binding_create_accepts_subject_id[/v1]` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_a2a_skills::test_a2a_structure_extract_skill_executes` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_a2a_skills::test_agent_card_advertises_structure_skills` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_phase25::test_phase25_mcp_extract_corpus_template` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_phase25::test_phase25_openapi_includes_structure_routes` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_phase25::test_phase25_rbac_reader_cannot_write` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_phase25::test_phase25_rest_surface` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_phase25::test_phase25_vdb_linkage` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_webui::test_structure_webui_page_renders_workflow_controls` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_Phase25.test_it_w28e603_webui::test_structure_webui_script_wires_workflows` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_StructureTransports.test_it_w28e603_structure_transports::test_structure_family_in_tools_list` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_StructureTransports.test_it_w28e603_structure_transports::test_structure_mcp_tools_call_real_execution` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_StructureTransports.test_it_w28e603_structure_transports::test_structure_rest_crud_lifecycle` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |
| `integration.IT_W28E603_StructureTransports.test_it_w28e603_structure_transports::test_structure_rest_requires_write_permission` | UNCLASSIFIED | pass | 2026-07-15 | `b74087f7` | |

## 3. Failures (detail)

_None._
