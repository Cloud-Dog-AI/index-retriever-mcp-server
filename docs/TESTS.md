---
template-id: T-TST
template-version: 1.1
applies-to: docs/TESTS.md
project: index-retriever-mcp-server
doc-last-updated: 2026-07-15T20:46:47Z
doc-git-commit: ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b
doc-git-branch: w28r-3016-index-retriever
doc-age-policy: 90d
doc-conformance-stamp: 2026-07-15T20:46:47Z
req-trace-version: 1.0
total-tests: 397
coverage-percent: 100
---

# Tests - index-retriever-mcp-server

## 2026-07-15 W28R-3016 retained qualification

`W28R-3016` executed the current service tree under CPython 3.13.14 and the
current Index Retriever WebUI under Node 22.22.0/pnpm 11.7.0. The service tree
was committed as `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b`; the WebUI tree was
merged as `c26566ccf3fe04e5d23cbc565b12901b1863209a`. CPython 3.12 was not used
for a full suite: the source-controlled runtime-contract gate rejects Python
earlier than 3.13, and that guard is not represented as 3.12 runtime parity.

| Lane | Runtime | Environment/config | Result | Immutable evidence |
|---|---|---|---|---|
| `W28R-3016` | CPython 3.12 | N/A | **NOT RUN** - Python 3.13 is the project runtime contract | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/python-final-premerge-version.log` |
| `W28R-3016` | CPython 3.13.14 | `tests/env-QT` | QT final: **52 passed, 0 failed/errors/skipped** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-post-ui-vendor-final.xml` |
| `W28R-3016` | CPython 3.13.14 | `tests/env-UT` | UT: **316 passed, 0 failed/errors/skipped**; branch coverage **72%** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/coverage-unit-junit.xml` |
| `W28R-3016` | CPython 3.13.14 | `tests/env-ST` | ST: **26 passed, 2 optional SQL-driver skips, 0 failed/errors**; real PostgreSQL target **1 passed** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-junit.xml` |
| `W28R-3016` | CPython 3.13.14 | `tests/env-IT` plus authorized Vault-derived local overlay | IT final: **64 passed, 3 optional unavailable-parser skips, 0 failed/errors** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-final-authorized-junit.xml` |
| `W28R-3016` | CPython 3.13.14 | `tests/env-AT` plus authorized Vault-derived local overlay | AT final: **26 passed, 0 failed/errors/skipped** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-final-authorized-junit.xml` |
| `W28R-3016` | N/A (Node/Playwright) | real local API/WebUI/MCP/A2A; API-key auth; one worker; zero retries | **76 passed, 0 failed/errors/skipped** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/ui/playwright-api-key-final-green.xml` |
| `W28R-3016` | N/A (Node/Playwright) | real local API/WebUI/MCP/A2A; cookie auth; one worker; zero retries | **12 passed, 0 failed/errors/skipped** | `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/ui/playwright-cookie-preprod-final-green.xml` |

Exact retained foreground commands:

```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
.venv/bin/python -m pytest tests/system --env tests/env-ST -q
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q
.venv/bin/python -m pytest tests/application --env tests/env-AT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT --cov=src --cov-branch
pnpm exec playwright test --config playwright.config.ts <non-preprod-specs> --workers=1 --retries=0 --reporter=line,junit
pnpm exec playwright test --config playwright.config.ts tests/e2e/preprod-deploy-smoke.spec.ts --workers=1 --retries=0 --reporter=line,junit
```

Adverse truth is retained rather than overwritten: the first full AT attempt
had 2 failures, the first fully configured IT attempt had 4 failures,
20 errors and 11 skips, the definitive API-key browser attempt had 67 passes and
9 failures, and the first post-vendoring QT attempt had 51 passes and 1 failure.
The generated history imports those JUnits and their corrected reruns in original
timestamp order. The targeted MySQL system probe also retained its initial
missing-driver failure and its corrected rerun after the frozen internal PyMySQL
release was added to the runtime contract. No external/public package lookup or
install was used.

The W28E-1882 candidate evidence commit
`84a9aa8725166695733ec8be7ebe4a4434c911f9` retains browser JUnits, including an
88/88 final pass and earlier failure/skip runs. It does not retain the required
exact command transcript or corrected `W28E-1882-*-R2` immutable tags. It is
therefore **NOT IMPORTED - provenance gap**, and none of those runs is added to
generated status/history. `docs/TEST-STATUS.md` and `docs/TEST-HISTORY.md` were
corrected to mark the candidates **NOT IMPORTED** while retaining adverse truth.

## 1. Tiers

| Tier | Present | Test functions | Evidence posture |
|---|---|---:|---|
| `QT` | Yes | 47 | Stream-A design-bound; execute in owning tier gate |
| `UT` | Yes | 235 | Stream-A design-bound; execute in owning tier gate |
| `ST` | Yes | 26 | Stream-A design-bound; execute in owning tier gate |
| `IT` | Yes | 63 | Stream-A design-bound + W28E-1805B IT1.25 IDAM cascade |
| `AT` | Yes | 26 | Stream-A design-bound; execute in owning tier gate |
| **Total** | - | **397** | Stream-A catalogue + W28E-1805B IT1.25 (IDAM role cascade) |

Standard commands:

```bash
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q
.venv/bin/python -m pytest tests/system --env tests/env-ST -q
.venv/bin/python -m pytest tests/integration --env tests/env-IT -q
.venv/bin/python -m pytest tests/application --env tests/env-AT -q
```

## 2. Coverage map

| Test ID | Tier | Use case | Requirement | Surface | Scenario | Variants | Env files | Known issue | Last run commit |
|---|---|---|---|---|---|---|---|---|---|
| T-AT-AT1-1 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_1/test_at1_1.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-2 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_2/test_at1_2.py (2 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-3 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_3/test_at1_3.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-4 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_4/test_at1_4.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-5 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_5/test_at1_5.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-6 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_6/test_at1_6.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-7 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_7/test_at1_7.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-8 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_8/test_at1_8_a2a_flow.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-8 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_8/test_at1_8_cross_backend_parity_fixture.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT1-9 | AT | UC-001 | FR-004 | mcp | tests/application/AT1_9/test_at1_9_no_fallback_backend_identity.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-1 | AT | UC-001 | FR-004 | mcp | tests/application/AT2_1/test_at2_1_multi_backend_consistency_chroma_qdrant.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-2 | AT | UC-001 | FR-004 | mcp | tests/application/AT2_2/test_at2_2_multi_backend_consistency_pgvector_opensearch.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-3 | AT | UC-002 | FR-009 | internal | tests/application/AT2_3/test_at2_3_multi_parser_quality_comparison.py (1 test functions) | module-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-4 | AT | UC-001 | FR-004 | mcp | tests/application/AT2_4/test_at2_4_multi_embedding_models.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-5 | AT | UC-001 | FR-004 | mcp | tests/application/AT2_5/test_at2_5_full_pipeline_e2e_per_backend.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT2-6-DATABASEE2E | AT | UC-001 | FR-004 | mcp | tests/application/AT2_6_DatabaseE2E/test_at2_6_database_e2e.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-AUTHDASHBOARD | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_AuthDashboard/test_webui_auth_dashboard.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-COLLECTIONCRUD | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_CollectionCrud/test_webui_collection_crud.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-COLLECTIONEDIT | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_CollectionEdit/test_webui_collection_edit.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-CWTESTIDCONTRACT | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_CwTestidContract/test_webui_cw_testid_contract.py (2 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-FILEUPLOAD | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_FileUpload/test_webui_file_upload.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-PROFILECRUD | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_ProfileCrud/test_webui_profile_crud.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-SECURITYADMIN | AT | UC-001 | FR-004, FR-018 | webui | tests/application/AT_WEBUI_SecurityAdmin/test_webui_security_admin.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-AT-AT-WEBUI-SOURCECONFIG | AT | UC-001 | FR-004 | webui | tests/application/AT_WEBUI_SourceConfig/test_webui_source_config.py (1 test functions) | function-level | tests/env-AT | - | affbc31 |
| T-UT-CT1-1 | UT | UC-005 | FR-003 | mcp | tests/contract/CT1_1/test_ct1_1_chroma_contract.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-CT1-2 | UT | UC-005 | FR-003 | mcp | tests/contract/CT1_2/test_ct1_2_qdrant_contract.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-CT1-3 | UT | UC-005 | FR-003 | mcp | tests/contract/CT1_3/test_ct1_3_backend_parity.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-CT1-4 | UT | UC-005 | FR-003 | mcp | tests/contract/CT1_4/test_ct1_4_infinity_contract.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-IT-IT1-1 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_1/test_it1_1.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-10 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_10/test_it1_10.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-11 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_11/test_it1_11.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-12 | IT | UC-001 | FR-007, FR-015 | mcp | tests/integration/IT1_12/test_it1_12.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-13 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_13/test_it1_13.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-14 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_14/test_it1_14.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-15 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_15/test_it1_15.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-16 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_16/test_it1_16.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-17 | IT | UC-002 | FR-009 | mcp | tests/integration/IT1_17/test_it1_17.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-18 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_18/test_it1_18_a2a_health_auth_matrix.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-19 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_19/test_it1_19_no_fallback_backend_identity.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-2 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_2/test_it1_2.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-20 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_20/test_it1_20_job_management_tools.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-21 | IT | UC-006 | FR-005 | mcp | tests/integration/IT1_21/test_it1_21_collection_rbac.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-21 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_21/test_it1_21_jobs_migration.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-22 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_22/test_it1_22_admin_rest_config_crud.py (2 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-23 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_23/test_it1_23_core_metadata.py (4 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-24 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_24/test_it1_24_openapi_contract.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-25 | IT | UC-007 | FR-008 | mcp | tests/integration/IT1_25_IdamCascade/test_it1_25_idam_role_cascade.py (2 test functions) | function-level | tests/env-IT | W28E-1805B D5 IDAM cascade | 1805B |
| T-IT-IT1-3 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_3/test_it1_3.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-4 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_4/test_it1_4.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-5 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_5/test_it1_5.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-6 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_6/test_it1_6.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-7 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_7/test_it1_7.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-8 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_8/test_it1_8.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT1-9 | IT | UC-001 | FR-007 | mcp | tests/integration/IT1_9/test_it1_9.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-1 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_1/test_it2_1_chroma_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-10 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_10/test_it2_10_marker_parser.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-11 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_11/test_it2_11_transformers_parser.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-12 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_12/test_it2_12_internal_parser.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-13 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_13/test_it2_13_ocr_provider_matrix.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-14 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_14/test_it2_14_table_extraction_matrix.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-15-DATABASESTARTUP | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_15_DatabaseStartup/test_it2_15_database_startup.py (1 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-16 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_16/test_it2_16_provenance_contract.py (3 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-2 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_2/test_it2_2_qdrant_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-3 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_3/test_it2_3_opensearch_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-4 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_4/test_it2_4_pgvector_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-5 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_5/test_it2_5_weaviate_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-6 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_6/test_it2_6_infinity_contract.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-7 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_7/test_it2_7_deepdoc_parser.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-8 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_8/test_it2_8_docling_parser.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT2-9 | IT | UC-001 | FR-007 | mcp | tests/integration/IT2_9/test_it2_9_mineru_parser.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT-W28D440E5 | IT | UC-002 | FR-009 | internal | tests/integration/IT_W28D440E5/test_hdro_live.py (1 test functions) | module-level | tests/env-IT | - | affbc31 |
| T-IT-IT-W28E603-PHASE25 | IT | UC-001 | FR-007 | mcp | tests/integration/IT_W28E603_Phase25/test_it_w28e603_a2a_skills.py (2 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT-W28E603-PHASE25 | IT | UC-001 | FR-007 | mcp | tests/integration/IT_W28E603_Phase25/test_it_w28e603_phase25.py (5 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT-W28E603-PHASE25 | IT | UC-001 | FR-007 | webui | tests/integration/IT_W28E603_Phase25/test_it_w28e603_webui.py (2 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-IT-IT-W28E603-STRUCTURETRANSPORTS | IT | UC-001 | FR-007 | mcp | tests/integration/IT_W28E603_StructureTransports/test_it_w28e603_structure_transports.py (4 test functions) | function-level | tests/env-IT | - | affbc31 |
| T-UT-PT1-1 | UT | UC-002 | FR-006 | mcp | tests/parser/PT1_1/test_pt1_1_backend_ingest_baseline.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-PT1-2 | UT | UC-002 | FR-006 | mcp | tests/parser/PT1_2/test_pt1_2_backend_search_latency.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-PT1-3 | UT | UC-002 | FR-006 | mcp | tests/parser/PT1_3/test_pt1_3_parser_throughput_comparison.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-QT-QT-COMPLIANCE | QT | UC-005 | NF-001 | internal | tests/quality/QT_COMPLIANCE/test_qt_migration_completeness.py (5 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-COMPLIANCE | QT | UC-005 | NF-001 | internal | tests/quality/QT_COMPLIANCE/test_qt_package_adoption.py (6 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-COMPLIANCE | QT | UC-006 | NF-003 | internal | tests/quality/QT_COMPLIANCE/test_qt_rules_compliance.py (10 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-COMPLIANCE | QT | UC-007 | NF-004 | internal | tests/quality/QT_COMPLIANCE/test_qt_traceability.py (3 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-COMPLIANCE | QT | UC-007 | NF-002 | internal | tests/quality/QT_COMPLIANCE/test_qt_vault_config_contract.py (7 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-LOGGINGCOMPLIANCE | QT | UC-007 | NF-002 | internal | tests/quality/QT_LoggingCompliance/test_logging_compliance.py (4 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-QT-QT-PACKAGE-COMPLIANCE | QT | UC-005 | NF-001 | internal | tests/quality/QT_PACKAGE_COMPLIANCE/test_package_compliance.py (12 test functions) | module-level | tests/env-QT | - | affbc31 |
| T-UT-QT1-1 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_1/test_qt1_1.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-QT1-2 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_2/test_qt1_2.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-QT1-3 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_3/test_qt1_3.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-QT1-4 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_4/test_qt1_4.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-QT1-5 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_5/test_qt1_5.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-QT1-6 | UT | UC-007 | FR-008 | mcp | tests/security/QT1_6/test_qt1_6.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-ST-ST1-1 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_1/test_st1_1.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-10 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_10/test_st1_10.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-11 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_11/test_st1_11.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-12 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_12/test_st1_12.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-13 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_13/test_st1_13_no_fallback_backend_identity.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-14 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_14/test_st1_14_database_migration.py (2 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-14 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_14/test_st1_14_database_migration_multibackend.py (2 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-15 | ST | UC-002 | FR-009 | mcp | tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py (3 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-2 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_2/test_st1_2.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-3 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_3/test_st1_3.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-4 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_4/test_st1_4.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-5 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_5/test_st1_5.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-6 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_6/test_st1_6.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-7 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_7/test_st1_7.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-8 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_8/test_st1_8.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST1-9 | ST | UC-006 | FR-005 | mcp | tests/system/ST1_9/test_st1_9.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST-INTEGRITYVERIFIER | ST | UC-006 | FR-005 | mcp | tests/system/ST_IntegrityVerifier/test_integrity_running.py (3 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST-LOGROTATION | ST | UC-006 | FR-005 | mcp | tests/system/ST_LogRotation/test_rotation_config.py (2 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-ST-ST-W28E603-STRUCTUREBACKENDMATRIX | ST | UC-006 | FR-005 | mcp | tests/system/ST_W28E603_StructureBackendMatrix/test_st_w28e603_structure_backend_matrix.py (1 test functions) | function-level | tests/env-ST | - | affbc31 |
| T-UT-UT1-1 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_1/test_ut1_1_config_loader_precedence.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-10 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_10/test_ut1_10_connector_s3_resolve.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-11 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_11/test_ut1_11_connector_webdav_resolve.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-12 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_12/test_ut1_12_convert_registry_selection.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-13 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_13/test_ut1_13_convert_pdf_extract.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-14 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_14/test_ut1_14_convert_office_extract.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-15 | UT | UC-001 | FR-010 | mcp | tests/unit/UT1_15/test_ut1_15_chunking_token_strategy.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-16 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_16/test_ut1_16_chunking_overlap.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-17 | UT | UC-001 | FR-010 | mcp | tests/unit/UT1_17/test_ut1_17_metadata_enrichment.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-18 | UT | UC-004 | FR-011 | mcp | tests/unit/UT1_18/test_ut1_18_dedupe_hash_detection.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-19 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_19/test_ut1_19_dedupe_size_mtime_detection.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-2 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_2/test_ut1_2_config_vault_integration.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-20 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_20/test_ut1_20_dedupe_policy_skip.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-21 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_21/test_ut1_21_dedupe_policy_replace.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-22 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_22/test_ut1_22_dedupe_policy_version.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-23 | UT | UC-001 | FR-012 | mcp | tests/unit/UT1_23/test_ut1_23_embedding_registry_lookup.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-24 | UT | UC-002 | FR-013 | mcp | tests/unit/UT1_24/test_ut1_24_vdb_registry_lookup.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-25 | UT | UC-001 | FR-014 | mcp | tests/unit/UT1_25/test_ut1_25_search_query_normalisation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-26 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_26/test_ut1_26_search_filter_validation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-27 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_27/test_ut1_27_job_model_validation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-28 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_28/test_ut1_28_idempotency_key_generation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-29 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_29/test_ut1_29_tool_definition_schemas.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-3 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_3/test_ut1_3_config_validation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-30 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_30/test_ut1_30_pipeline_progress_events.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-31 | UT | UC-007 | CS-001, CS-002, CS-003, CS-005, CS-008, CS-011, FR-001 | mcp | tests/unit/UT1_31/test_ut1_31_server_runtime_paths.py (17 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-32 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_32/test_ut1_32_support_module_paths.py (16 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-33 | UT | UC-005 | FR-003, FR-015 | mcp | tests/unit/UT1_33/test_ut1_33_service_branch_paths.py (4 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-34 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_34/test_ut1_34_service_and_adapter_branches.py (13 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-35 | UT | UC-005 | FR-017 | mcp | tests/unit/UT1_35/test_ut1_35_coverage_closure.py (7 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-36 | UT | UC-002 | FR-013 | mcp | tests/unit/UT1_36/test_ut1_36_service_vdb041_branches.py (8 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-37 | UT | UC-002 | FR-013 | mcp | tests/unit/UT1_37/test_ut1_37_mcp_vdb041_dispatch.py (3 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-38 | UT | UC-007 | FR-001 | mcp | tests/unit/UT1_38/test_ut1_38_a2a_auth_contract.py (5 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-39 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_39/test_ut1_39_runtime_config_loader_paths.py (3 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-4 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_4/test_ut1_4_profile_model_validation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-40 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_40/test_ut1_40_database_abstraction.py (2 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-40 | UT | UC-005 | FR-016 | mcp | tests/unit/UT1_40/test_ut1_40_tool_registry.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-41 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_41/test_ut1_41_connector_ftp.py (5 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-42 | UT | UC-007 | CS-004, CS-006, CS-007, CS-009, CS-010, CS-012, CS-013, FR-002 | mcp | tests/unit/UT1_42/test_ut1_42_connector_gdrive.py (5 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-43 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_43/test_ut1_43_embedding_dimension_validation.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-44 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_44/test_ut1_44_admin_config_crud.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-45 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_45/test_ut1_45_jobs_migration.py (3 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-45 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_45/test_w28d314_resource_pool_and_job_types.py (5 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-46 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_46/test_ut1_46_w28c427r5_connector_matrix.py (3 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-46-JOBLIFECYCLESIMULATION | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_46_JobLifecycleSimulation/test_job_lifecycle.py (4 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-47 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_47/test_ut1_47_core_metadata.py (12 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-48 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_48/test_ut1_48_admin_empty_state_hint.py (2 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-5 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_5/test_ut1_5_rbac_policy_eval.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-6 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_6/test_ut1_6_connector_scope_enforcement.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-7 | UT | UC-002 | FR-006 | mcp | tests/unit/UT1_7/test_ut1_7_audit_event_shape.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-8 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_8/test_ut1_8_audit_redaction.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT1-9 | UT | UC-001 | FR-002 | mcp | tests/unit/UT1_9/test_ut1_9_connector_filesystem_resolve.py (1 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT-AUDITLOGFORMAT | UT | UC-001 | FR-002 | mcp | tests/unit/UT_AuditLogFormat/test_audit_log_format.py (4 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT-BOOTSTRAP | UT | UC-001 | FR-002 | mcp | tests/unit/UT_Bootstrap/test_bootstrap_seed_apply.py (20 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT-W28D440E1 | UT | UC-001 | FR-002 | mcp | tests/unit/UT_W28D440E1/test_ingest_text_robustness.py (9 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT-W28D440E5 | UT | UC-002 | FR-009 | internal | tests/unit/UT_W28D440E5/test_hdro_extractor.py (9 test functions) | module-level | tests/env-UT | - | affbc31 |
| T-UT-UT-W28E603-PHASE25 | UT | UC-001 | FR-002 | mcp | tests/unit/UT_W28E603_Phase25/test_ut_w28e603_phase25.py (12 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-UT-W28E603-STRUCTURE | UT | UC-001 | FR-002 | mcp | tests/unit/UT_W28E603_Structure/test_ut_w28e603_structure.py (12 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-W28A295-MULTIPROFILE-LOAD | UT | UC-001 | FR-002 | mcp | tests/unit/test_w28a295_multiprofile_load.py (2 test functions) | function-level | tests/env-UT | - | affbc31 |
| T-UT-W28D443-TB-PROFILE-DURABILITY | UT | UC-001 | FR-002 | mcp | tests/unit/test_w28d443_tb_profile_durability.py (4 test functions) | function-level | tests/env-UT | - | affbc31 |

## 3. Scenarios

The catalogue covers auth and RBAC denials, data-plane ingest/search/retrieve, parser/OCR/table extraction, VDB backend parity, async job management, audit/logging, WebUI/API parity, IDAM route handling, and negative validation paths. Stream-A binds design coverage only; Stream-B owns fresh live execution evidence.

## 4. Running

Use the tier commands above with the committed `tests/env-*` overlays. Live tiers require the normal Vault-sourced environment described in `RULES.md` and the service-local `AGENT-LESSONS.md`.

## 5. Cross-references

- Requirements: `docs/REQUIREMENTS.md`
- Use cases: `docs/ROLES-AND-USECASES.md`
- Scope map: `tests/SCOPE-MAP.md`
- Generated coverage: `docs/REQ-COVERAGE.md`
- Warranty: `docs/WARRANTY-1.0RC01.md`
- Test-pack reference: `tests/fixtures/TEST-PACK-REFERENCE.md`

## 6. Project-specific notes

W28E-1805A replaces residual archived design anchors with semantic requirement bindings. W28E-1805C closes the Stream-C WebUI/E2E local Docker path with a clean 76/76 browser suite against `cloud-dog/index-retriever-mcp-server:w28e-1805c-local`.

W28E-1805C raw closeout artefacts:

- Unit search backfill: `working/evidence/W28E-1805C/current/logs/service-unit-search-local-backfill-env.log`.
- Unit Web tool proxy: `working/evidence/W28E-1805C/current/logs/service-unit-web-tool-proxy-api-forward-env-rerun.log`.
- Local Docker build: `working/evidence/W28E-1805C/current/logs/local-docker-build-search-backfill-vault-simple.log`.
- Full WebUI/E2E: `working/evidence/W28E-1805C/current/logs/local-docker-webui-playwright-search-backfill-full-clean.log`.


<!-- W28E-1854 PS-PREPROD-DEPLOY-SMOKE rollout (2026-06-29) -->

## W28E-1854 — PS-PREPROD-DEPLOY-SMOKE (preprod deployment smoke)

Binding standard: `cloud-dog-ai-platform-standards/docs/standards/PS-PREPROD-DEPLOY-SMOKE.md`
(PDS-001..PDS-013 + sibling sentinels). Lesson origin: AGENT-LESSONS §6.157 — a
deployed service can answer health checks while its WebUI login flow crashes blank
post-login. Health-only / route-only / local-only proof is NOT acceptance; this
gate runs a real browser AFTER the final deployed digest is live.

- **Smoke command (service entry point):**
  `E2E_WEB_PASSWORD="<approved preprod admin password>" bash tests/smoke/run-preprod-deploy-smoke.sh`
- **SSOT spec:** `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/preprod-deploy-smoke.spec.ts`
- **Dedicated Playwright config (no local webServer):** `cloud-dog-ai-ui-monorepo/apps/index-retriever/playwright.preprod-smoke.config.ts`
- **Required config keys (no hardcoded secrets):** `E2E_BASE_URL`
  (default `https://indexretriever0.cloud-dog.net`), `E2E_WEB_USERNAME` (default `admin`),
  `E2E_WEB_PASSWORD` / `CLOUD_DOG_WEB_LOGIN_PASSWORD` (approved preprod env / Vault
  `cloud_dog_ai/config:dev.services.indexretriever0.web_password`).
- **Expected auth mode:** cookie session login at canonical `/login`
  (`/ui/login` → 308 → `/login`); anonymous `/auth/me` → 401 or `{user:null}` (no principal leak).
- **Canonical page inventory (PDS-009):** `/`, `/admin/users`, `/admin/groups`, `/admin/api-keys`, `/admin/roles`, `/admin/rbac`, `/api-docs`, `/mcp-console`, `/a2a-console`, `/jobs`, `/settings`.
- **Service-specific page inventory (PDS-010, hard-navigated — the crash-class guard):** `/collections`, `/ingest-search`, `/structure/documents`, `/observability`.
- **Cleanliness bar (PDS-012):** zero uncaught page errors, zero fatal console
  errors, zero 5xx, zero unexpected 4xx (shared `@cloud-dog/idam` best-effort
  capability probes are the only tolerated 4xx; the crash discriminator
  pageerror + blank `#root` + 5xx is asserted with zero tolerance).
- **Evidence output location:** `working/preprod-deploy-smoke/` (gitignored test
  output: JUnit `preprod-deploy-smoke.junit.xml`, HTML report, traces, screenshots).

## W28E-1882 deployed WebUI final

- **Run timestamp (UTC):** `2026-07-14T10:00:14.382Z`
- **Tested source:** `2dd688bb4bb7b4504d752168736cfc575495c1ec` (`main`)
- **Runtime:** N/A (Node/Playwright)
- **Environment:** deployed preprod with approved runtime/Vault credentials
- **Command:** `bash /opt/iac/Development/cloud-dog-ai/tmp/W28E-1882/run-index-retriever.sh FINAL`
- **Result:** PASS — 88 tests, 0 failures, 0 errors, 0 skipped
- **Evidence:** `W28E-1882-FINAL-PROOF-R2:working/evidence/W28E-1882/current/raw/index-retriever/index-retriever.FINAL.junit.xml`
