---
template-id: T-TSH
template-version: 1.0
applies-to: docs/TEST-HISTORY.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-07-15T20:46:47.881889Z
doc-git-commit: ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b
doc-git-branch: w28r-3016-index-retriever
doc-source-shas: []
doc-age-policy: indefinite
doc-conformance-stamp: 2026-07-15T20:46:47.881889Z
---

# index-retriever-mcp-server — TEST-HISTORY

> **Template version:** T-TSH v1.0 — appended to by `scripts/update-test-state.py`. Roll-archive to `archive/test-history/<YYYY-MM>.md` when >500 lines.

## Runs (most recent first)

### 2026-07-15T22:36:27.353420+00:00 — W28R-3016
- Commit: `f014476b8e810c83bf61e8dc957269e38dc2baaa` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-ST + Vault-provided W28E603_MATRIX_POSTGRESQL_URL + W28E603_MATRIX_MYSQL_URL`
- Command: `.venv/bin/python -m pytest tests/system --env tests/env-ST -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-all-backends-zero-skip-junit.xml`
- Totals: 28 / P 28 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T22:36:27.245415+00:00 — W28R-3016
- Commit: `f014476b8e810c83bf61e8dc957269e38dc2baaa` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-QT`
- Command: `.venv/bin/python -m pytest tests/quality --env tests/env-QT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-mysql-contract-final-junit.xml`
- Totals: 52 / P 52 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T21:22:47.820302Z — W28R-3016
- Commit: `b74087f738679b3f1fef1744ceaadd44351e1d93` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT-local-docker + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/integration/IT1_7/test_it1_7.py::test_mcp_tool_execution --env tests/env-IT-local-docker -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it1-7-final-formatted-green.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T21:21:01.315484Z — W28R-3016
- Commit: `b74087f738679b3f1fef1744ceaadd44351e1d93` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT-local-docker + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/integration --env tests/env-IT-local-docker -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it-final-image-green.xml`
- Totals: 67 / P 64 / F 0 / E 0 / S 3
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T21:14:21.512417Z — W28R-3016
- Commit: `b74087f738679b3f1fef1744ceaadd44351e1d93` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT-local-docker + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/integration/IT1_7/test_it1_7.py::test_mcp_tool_execution --env tests/env-IT-local-docker -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it1-7-final-image-green.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T21:14:03.536280Z — W28R-3016
- Commit: `b74087f738679b3f1fef1744ceaadd44351e1d93` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT-local-docker; VAULT_TOKEN absent at preflight`
- Command: `.venv/bin/python -m pytest tests/integration/IT1_7/test_it1_7.py::test_mcp_tool_execution --env tests/env-IT-local-docker -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it1-7-final-image-rerun.xml`
- Totals: 1 / P 0 / F 0 / E 1 / S 0
- Delta: new-fails 1 | newly-green 1

### 2026-07-15T21:11:51.155265Z — W28R-3016
- Commit: `decbbc652101ba7cd2bda96a27cce3673b8ecab8` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT-local-docker + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/integration --env tests/env-IT-local-docker -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/local-docker/it-final-image.xml`
- Totals: 67 / P 63 / F 1 / E 0 / S 3
- Delta: new-fails 1 | newly-green 0

### 2026-07-15T20:46:47.881889Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-QT`
- Command: `.venv/bin/python -m pytest tests/quality --env tests/env-QT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-post-ui-vendor-final.xml`
- Totals: 52 / P 52 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 1

### 2026-07-15T20:46:03.318767Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-QT`
- Command: `.venv/bin/python -m pytest tests/quality --env tests/env-QT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-post-ui-vendor.xml`
- Totals: 52 / P 51 / F 1 / E 0 / S 0
- Delta: new-fails 1 | newly-green 0

### 2026-07-15T20:41:38.291Z — W28R-3016
- Commit: `c26566ccf3fe04e5d23cbc565b12901b1863209a` (w28r-3016-index-retriever-ui)
- Runtime: N/A (Node/Playwright 22.22.0)
- Environment: `real local API/WebUI/MCP/A2A; cookie auth; workers=1; retries=0; service tree ba37248c`
- Command: `pnpm exec playwright test --config playwright.config.ts tests/e2e/preprod-deploy-smoke.spec.ts --workers=1 --retries=0 --reporter=line,junit`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/ui/playwright-cookie-preprod-final-green.xml`
- Totals: 12 / P 12 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T20:30:53.198Z — W28R-3016
- Commit: `c26566ccf3fe04e5d23cbc565b12901b1863209a` (w28r-3016-index-retriever-ui)
- Runtime: N/A (Node/Playwright 22.22.0)
- Environment: `real local API/WebUI/MCP/A2A; API-key auth; workers=1; retries=0; service tree ba37248c`
- Command: `pnpm exec playwright test --config playwright.config.ts <non-preprod-specs> --workers=1 --retries=0 --reporter=line,junit`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/ui/playwright-api-key-final-green.xml`
- Totals: 76 / P 76 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 9

### 2026-07-15T19:53:21.717Z — W28R-3016
- Commit: `c26566ccf3fe04e5d23cbc565b12901b1863209a` (w28r-3016-index-retriever-ui)
- Runtime: N/A (Node/Playwright 22.22.0)
- Environment: `real local API/WebUI/MCP/A2A; API-key auth; workers=1; retries=0`
- Command: `pnpm exec playwright test --config playwright.config.ts <non-preprod-specs> --workers=1 --retries=0 --reporter=line,junit`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/ui/playwright-api-key-definitive-junit.xml`
- Totals: 76 / P 67 / F 9 / E 0 / S 0
- Delta: new-fails 9 | newly-green 0

### 2026-07-15T19:16:11.237217Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-UT`
- Command: `.venv/bin/python -m pytest tests/unit --env tests/env-UT --cov=src --cov-branch -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/coverage-unit-junit.xml`
- Totals: 316 / P 316 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T19:03:51.032424Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-AT + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/application --env tests/env-AT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-final-authorized-junit.xml`
- Totals: 26 / P 26 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T18:53:41.583933Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT + authorized Vault-derived environment`
- Command: `.venv/bin/python -m pytest tests/integration --env tests/env-IT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-final-authorized-junit.xml`
- Totals: 67 / P 64 / F 0 / E 0 / S 3
- Delta: new-fails 0 | newly-green 4

### 2026-07-15T18:50:12.202726Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT`
- Command: `.venv/bin/python -m pytest tests/integration --env tests/env-IT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-final-junit.xml`
- Totals: 67 / P 32 / F 4 / E 20 / S 11
- Delta: new-fails 24 | newly-green 0

### 2026-07-15T18:48:46.561851Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-AT + isolated UI worktree`
- Command: `.venv/bin/python -m pytest tests/application/AT_WEBUI_SourceConfig --env tests/env-AT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-webui-source-config-targeted-junit.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T18:48:01.466736Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-AT + isolated PLATFORM_VDB_ROOT`
- Command: `.venv/bin/python -m pytest tests/application/AT1_8/test_at1_8_cross_backend_parity_fixture.py --env tests/env-AT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-parity-targeted-final-junit.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T18:43:46.023173Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-AT`
- Command: `.venv/bin/python -m pytest tests/application/AT1_8/test_at1_8_cross_backend_parity_fixture.py --env tests/env-AT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-parity-targeted-junit.xml`
- Totals: 1 / P 0 / F 0 / E 1 / S 0
- Delta: new-fails 1 | newly-green 2

### 2026-07-15T18:24:08.916346Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-AT`
- Command: `.venv/bin/python -m pytest tests/application --env tests/env-AT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/at-junit.xml`
- Totals: 26 / P 24 / F 2 / E 0 / S 0
- Delta: new-fails 2 | newly-green 0

### 2026-07-15T18:23:50.687725Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT + authorized MinerU endpoint`
- Command: `.venv/bin/python -m pytest tests/integration/IT2_9 --env tests/env-IT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-mineru-junit.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 1

### 2026-07-15T16:21:27.341782Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT + tests/env-REQUIRE-ALL-PARSERS`
- Command: `.venv/bin/python -m pytest tests/integration/IT2_7 tests/integration/IT2_8 tests/integration/IT2_9 tests/integration/IT2_10 tests/integration/IT2_11 tests/integration/IT2_12 --env tests/env-IT --env tests/env-REQUIRE-ALL-PARSERS -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-parsers-junit.xml`
- Totals: 8 / P 7 / F 1 / E 0 / S 0
- Delta: new-fails 1 | newly-green 11

### 2026-07-15T16:10:55.410138Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-IT`
- Command: `.venv/bin/python -m pytest tests/integration --env tests/env-IT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/it-junit.xml`
- Totals: 71 / P 57 / F 11 / E 0 / S 3
- Delta: new-fails 11 | newly-green 1

### 2026-07-15T16:10:03.637311Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-ST + tests/env-DB-mysql`
- Command: `.venv/bin/python -m pytest tests/system/ST1_14 --env tests/env-ST --env tests/env-DB-mysql -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-mysql-junit.xml`
- Totals: 1 / P 0 / F 1 / E 0 / S 0
- Delta: new-fails 1 | newly-green 0

### 2026-07-15T16:10:03.636962Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-ST + tests/env-DB-postgresql`
- Command: `.venv/bin/python -m pytest tests/system/ST1_14 --env tests/env-ST --env tests/env-DB-postgresql -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-postgresql-junit.xml`
- Totals: 1 / P 1 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T16:08:21.271588Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-ST`
- Command: `.venv/bin/python -m pytest tests/system --env tests/env-ST -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/st-junit.xml`
- Totals: 28 / P 26 / F 0 / E 0 / S 2
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T16:05:57.928998Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-UT`
- Command: `.venv/bin/python -m pytest tests/unit --env tests/env-UT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/ut-junit.xml`
- Totals: 316 / P 316 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-15T16:04:19.568437Z — W28R-3016
- Commit: `ba37248cbf0b2d21e87a6e02dd28af3fdb6d214b` (w28r-3016-index-retriever)
- Runtime: CPython 3.13.14
- Environment: `tests/env-QT`
- Command: `.venv/bin/python -m pytest tests/quality --env tests/env-QT -q`
- Evidence: `W28R-3016-EVIDENCE:working/evidence/W28R-3016/current/raw/tests/qt-junit.xml`
- Totals: 58 / P 58 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-14T10:00:14.382Z — W28E-1882
- Commit: `2dd688bb4bb7b4504d752168736cfc575495c1ec` (main)
- Runtime: N/A (Node/Playwright)
- Environment: `deployed preprod; approved runtime/Vault credentials; service E2E_BASE_URL`
- Command: `bash /opt/iac/Development/cloud-dog-ai/tmp/W28E-1882/run-index-retriever.sh FINAL`
- Evidence: `W28E-1882-FINAL-PROOF-R2:working/evidence/W28E-1882/current/raw/index-retriever/index-retriever.FINAL.junit.xml`
- Totals: 88 / P 88 / F 0 / E 0 / S 0
- Delta: new-fails 0 | newly-green 0

### 2026-07-14T17:38:04Z - W28E-1863 / W28E-1882 / W28R-3016 candidate review
- Runtime: N/A (no evidence-qualified run imported); CPython 3.12, CPython 3.13, and Node/Playwright reviewed separately.
- Environment: NOT RECORDED with every mandatory provenance field.
- Command: NOT RECORDED as a literal foreground invocation in immutable evidence.
- Evidence: `docs/TEST-CANDIDATE-DISPOSITIONS-2026-07-08-14.md`.
- Totals: NOT IMPORTED; legacy 421-pass/5-skip and browser pass/failure/skip summaries remain candidate truth only.
- Disposition: documentation review, not a test run; W28R-3016 was undispatched.

### 2026-06-25T08:50:39+01:00
- Commit: `W28E-1805C-closeout` (main)
- Totals: 76 / P 76 / F 0 / S 0
- Delta: local Docker WebUI/E2E send-back correction; full clean-container run green.

### 2026-06-17T11:09:46.029469+00:00
- Commit: `722fe3ec37069c901bde5b9fbdf6d6825fbbdcc6` (W28C-1714-100pct-fix)
- Totals: 22 / P 22 / F 0 / S 0
- Delta: new-fails 0 | newly-green 1

### 2026-06-13T10:59:11.759580+00:00
- Commit: `5501696a8c127e6629a846a9b6a80fc89a2351f2` (w28a-749-idam)
- Totals: 346 / P 340 / F 1 / S 5
- Delta: new-fails 1 | newly-green 1

### 2026-06-13T10:18:36.645391+00:00
- Commit: `5501696a8c127e6629a846a9b6a80fc89a2351f2` (w28a-749-idam)
- Totals: 346 / P 340 / F 1 / S 5
- Delta: new-fails 1 | newly-green 0

### 2026-06-12T12:00:00Z
- Commit: `5cba8eb76245a4d7ba5af6f0b3b765199a6f6ee6` (main)
- Totals: N / P n / F n / S n
- Delta: new-fails 0 | newly-green 0
