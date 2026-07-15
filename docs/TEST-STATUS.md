---
template-id: T-TSS
template-version: 1.0
project: index-retriever-mcp-server
doc-last-updated: 2026-07-15T20:46:47.881889Z
doc-git-commit: ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b
doc-git-branch: w28r-3016-index-retriever
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-15T20:46:47.881889Z
---

# index-retriever-mcp-server — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-07-15T20:46:47.881889Z
- **Commit:** `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (`w28r-3016-index-retriever`)
- **Runtime:** CPython 3.13.14
- **Lane:** `W28R-3016`
- **Environment:** `tests/env-QT`
- **Command:** `.venv/bin/python -m pytest tests/quality --env tests/env-QT -q`
- **Evidence:** `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-post-ui-vendor-final.xml`
- **Totals:** 52 tests | 52 passed | 0 failed | 0 errors | 0 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `quality.QT_COMPLIANCE.test_qt_migration_completeness::test_cloud_dog_config_drives_loader` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_bespoke_auth_hooks` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_raw_fastapi_instantiation` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_migration_completeness::test_no_yaml_safe_load_for_config` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_migration_completeness::test_os_environ_usage_is_confined_to_runtime_boundaries` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_api_package_adoption` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_config_package_adoption` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_db_and_vdb_package_adoption` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_idam_package_adoption` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_logging_package_adoption` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_package_adoption::test_pyproject_declares_required_platform_packages` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc01_no_hardcoded_urls_or_loopback` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc02_no_hardcoded_credentials` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc03_external_imports_not_scattered` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc04_headers_and_docstring_coverage` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc05_no_mocking_patterns_in_it_at` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc06_no_pytest_skip_in_it_at` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc07_no_raw_vault_template_in_py_tests` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc08_tier_env_files_are_connected_to_runtime` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc09_no_stub_placeholders` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_rules_compliance::test_rc10_no_american_spelling_in_user_facing_errors` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_traceability::test_delivery_matrix_generated_for_all_requirements` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_traceability::test_traceability_gap_report_generated` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_traceability::test_traceability_source_docs_exist` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_defaults_yaml_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_defaults_yaml_has_no_literal_secrets` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_env_files_avoid_obvious_literal_secret_values` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_env_files_have_valid_vault_expression_syntax` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_env_tiers_exist` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_no_literal_secrets_in_source` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_COMPLIANCE.test_qt_vault_config_contract::test_sensitive_env_keys_use_vault_or_explicit_test_values` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_LoggingCompliance.test_logging_compliance::test_audit_events_doc_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_integrity_config` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_retention_config` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_LoggingCompliance.test_logging_compliance::test_defaults_yaml_has_rotation_config` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_external_pip_auth_helper::test_external_netrc_is_wired_only_as_a_buildkit_secret` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_external_pip_auth_helper::test_frozen_lock_jobs_pin_matches_project_runtime_contract` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_external_pip_auth_helper::test_private_dev_build_requires_external_netrc_helper` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_licence_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_auth` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_config_manager` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_bespoke_logging` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_direct_llm_calls` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_hardcoded_secrets` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_internal_hostnames` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_no_memory_queue` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_readme_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_runtime_config_endpoint` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_server_control_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_PACKAGE_COMPLIANCE.test_package_compliance.TestPackageCompliance::test_ui_dist_exists` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_RUNTIME.test_python313_contract::test_project_and_container_runtime_contract_is_python_313` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |
| `quality.QT_RUNTIME.test_python313_contract::test_tests_execute_on_cpython_313` | UNCLASSIFIED | pass | 2026-07-15 | `ba37248c` | |

## 3. Failures (detail)

_None._
