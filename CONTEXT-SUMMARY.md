# Context Summary

## W28E-1878 — IR-23 demo-profile gating (2026-07-11)
- Demo/test profiles (multilang, NATO, Ukraine, Transparent Borders x6) were moved
  out of the shipped `defaults.yaml` into the opt-in `config/demo-profiles.yaml`.
- New gate `index.demo_profiles.{enabled,path}` (env `CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED`);
  default OFF. A clean install now lists only the `default` profile
  (`profiles_list == ['default']`); demo/dev/preprod opt in to load the demo suite.
- Loader refactored in `src/index_tools/tools/service.py` (`_ingest_profiles_mapping` +
  `_load_demo_profiles`, resolved through `cloud_dog_config` so `${...}` expressions
  resolve). Tests: `tests/unit/test_w28e1878_demo_profiles_gate.py`, updated
  `test_w28a295_multiprofile_load.py` and `test_w28d443_tb_profile_durability.py`.
- See README "Storage profiles" for operator opt-in.

## Current State
- Project: `index-retriever-mcp-server`
- Working directory: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`
- Latest completed instruction in this handoff: `W28A-513-FIX-INDEXRETRIEVER-E2E-GAPS`
- Current status of that instruction: `PASS`

## What Was Completed
- Added requirement coverage for the 4 documented gaps:
  - `FR-09A` OCR provider support and selection
  - `FR-10A` chunking strategy matrix
  - `FR-14A` retrieval output contract and effective output modes
  - `FR-16A` complete MCP tool inventory contract
- Updated both requirement/test documentation copies:
  - `docs/REQUIREMENTS.md`
  - `REQUIREMENTS.md`
  - `docs/TESTS.md`
  - `TESTS.md`
- Added/updated test coverage:
  - `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py`
  - `tests/unit/UT1_40/test_ut1_40_tool_registry.py`
- Fixed WebUI test harness/runtime alignment:
  - `tests/application/_webui_playwright.py`
  - monorepo Playwright spec selector fixes in `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/*`
- Removed committed WebUI password values from repo env files:
  - `tests/env-AT`
  - `tests/env-ST`
- Built and pushed Docker image
- Executed Terraform deploy path for preprod
- Verified preprod health and targeted preprod ST coverage

## Important Fixes Made During This Run

### 1. WebUI / AT integrity fix
- Problem: committed `CLOUD_DOG_WEB_LOGIN_PASSWORD` values caused integrity-gate failure.
- Fix:
  - removed password from committed env files
  - kept browser login password shell-only at execution time
  - forced Playwright wrappers to use the already-started runtime via `E2E_USE_EXISTING_SERVER=1`
- Files:
  - `tests/env-AT`
  - `tests/env-ST`
  - `tests/application/_webui_playwright.py`

### 2. ST1.15 provider propagation bug
- Problem: `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py` created collections on one provider but the delegated ingest path upserted through the default backend because `provider_id` was not propagated through the actual write call.
- Effect:
  - preprod run hit Qdrant unexpectedly and failed with `404` on `/collections/.../points?wait=true`
  - this looked like a Qdrant readiness problem at first, but the real root cause was provider mismatch inside the test helper
- Fix:
  - the helper now builds `Record` objects directly and calls `vdb_client.upsert_records(..., provider_id=provider_id)`
  - backend-agnostic coverage now explicitly prefers `chroma` when available through `_coverage_provider()`
- File:
  - `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py`

### 3. Shared `platform-vdb` Qdrant hardening
- I also patched the shared Qdrant adapter while investigating the preprod behaviour.
- Files changed in shared package:
  - `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-vdb/cloud_dog_vdb/adapters/qdrant.py`
  - `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-vdb/tests/unit/UT1.3_QdrantAdapter/test_qdrant_unit.py`
- Final conclusion from direct backend debugging:
  - raw Qdrant create/get/write/delete worked fine against `https://qdrant.cloud-dog.net`
  - the decisive failure for W28A-513 was in the project test helper’s provider propagation, not raw Qdrant connectivity
- The shared-package unit test evidence is still useful and passed:
  - `working/W28A-513-platform-vdb-qdrant-ut-r2.log`

## Final Verified Results

### Integrity
- `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
- Result: `WARN — 27 warnings, 0 failures`
- Evidence:
  - `working/W28A-513-verify-test-integrity-r4.log`

### Tier Results
- QT: `47 passed`
  - `working/W28A-513-qt-final.log`
- UT: `111 passed`
  - `working/W28A-513-ut-final.log`
- ST: `25 passed in 17.85s`
  - `working/W28A-513-st-final-r2.log`
- IT: `39 passed`
  - `working/W28A-513-it-final.log`
- AT: `24 passed, 0 failed, 2 warnings in 327.38s`
  - `working/W28A-513-at-final-rerun5.log`
- No-Vault proof:
  - `working/W28A-513-it-no-vault.log`

### Targeted ST1.15 verification
- Local: `3 passed in 5.26s`
  - `working/W28A-513-st1_15-local-r3.log`
- Preprod runtime path: `3 passed in 5.54s`
  - `working/W28A-513-preprod-st1_15-r6.log`

### Targeted WebUI rerun
- `2 passed in 18.88s`
- Evidence:
  - `working/W28A-513-at-webui-target-r9.log`

## Deploy / Preprod State
- Docker build log:
  - `working/W28A-513-docker-build.log`
- Docker push log:
  - `working/W28A-513-docker-push.log`
- Pushed image digest:
  - `sha256:3ff0f23d16b744b13fe9426326320aa65a4a4555acb42001c3ed9c5acf58af93`
- Terraform logs:
  - `working/W28A-513-terraform-plan.log`
  - `working/W28A-513-terraform-apply.log`
- Terraform result:
  - `No changes. Your infrastructure matches the configuration.`
  - `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.`
- Preprod health:
  - `curl -sk https://indexretriever0.cloud-dog.net/health`
  - response saved in `working/W28A-513-preprod-health.json`

## Key Files Touched In This Repo
- `docs/REQUIREMENTS.md`
- `REQUIREMENTS.md`
- `docs/TESTS.md`
- `TESTS.md`
- `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py`
- `tests/unit/UT1_40/test_ut1_40_tool_registry.py`
- `tests/application/_webui_playwright.py`
- `tests/env-AT`
- `tests/env-ST`

## Key External Files Touched In This Run
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/collection-crud.spec.ts`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/collection-edit.spec.ts`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/profile-crud.spec.ts`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/security-admin.spec.ts`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/e2e/source-config.spec.ts`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/tests/fixtures.ts`
- `cloud-dog-ai-platform-standards/packages/backend/platform-vdb/cloud_dog_vdb/adapters/qdrant.py`
- `cloud-dog-ai-platform-standards/packages/backend/platform-vdb/tests/unit/UT1.3_QdrantAdapter/test_qdrant_unit.py`

## Final Report
- `working/W28A-513-FIX-E2E-GAPS-REPORT.md`

## Rules / Constraints Still In Force For Next Agent
- No SSH
- No iptables / Shorewall / firewall changes
- Terraform only for deploy path
- No custom Vault resolvers
- No `cloud_dog_config` bypass
- No completion claim without exact evidence
- Use shell-only secret injection for WebUI login credentials; do not commit login passwords into repo env files again

## Recommended Starting Point For Next Agent
1. Read `RULES.md`
2. Read this file: `CONTEXT-SUMMARY.md`
3. Read the latest report:
   - `working/W28A-513-FIX-E2E-GAPS-REPORT.md`
4. If continuing from current repo state, treat the current dirty tree as deliberate baseline and inspect `git status` before touching anything
