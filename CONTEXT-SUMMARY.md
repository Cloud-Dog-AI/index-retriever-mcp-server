# index-retriever-mcp-server — Context Summary

**Last updated:** 2026-02-22  
**Status:** Integrity remediation complete with current evidence

---

## Verified Results (Current)

- Integrity verifier:
  - Command: `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
  - Result: `PASS: 10, FAIL: 0, WARN: 0`

- IT without Vault (must fail, not skip):
  - Command: `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT -q -rs`
  - Result: `12 errors`, explicit `missing VAULT_TOKEN`, `0 skipped`

- Tier runs with Vault sourced (`set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`):
  - `python3 -m pytest tests/unit --env tests/env-UT -q -rs` → `61 passed`, `0 skipped`
  - `python3 -m pytest tests/system --env tests/env-ST -q -rs` → `12 passed`, `0 skipped`
  - `python3 -m pytest tests/integration --env tests/env-IT -q -rs` → `12 passed`, `0 skipped`
  - `python3 -m pytest tests/application --env tests/env-AT -q -rs` → `5 passed`, `0 skipped`
  - `python3 -m pytest tests/security --env tests/env-QT -q -rs` → `5 passed`, `0 skipped`
  - `python3 -m pytest tests/contract --env tests/env-IT -q -rs` → `3 passed`, `0 skipped`

- Full suite + coverage with Vault sourced:
  - Command: `python3 -m pytest tests/ --env tests/env-UT --env tests/env-ST --env tests/env-IT --env tests/env-AT --env tests/env-QT -q -rs --cov=src --cov-report=term-missing`
  - Result: `98 passed`, `0 failed`, `0 skipped`, `2 warnings`
  - Coverage: `100%` (`1122 statements`, `0 missed`)

---

## Compliance Remediation Completed

- Removed ST local-runtime usage and enforced live preflight for ST/IT/AT/QT/CT:
  - `tests/system/ST1_1` through `tests/system/ST1_12`
  - `tests/conftest.py`
  - `tests/env-ST`

- Eliminated hardcoded `/tmp` paths from runtime/test code where corrected in this wave:
  - `src/index_server/api_server.py`
  - `src/index_server/mcp_server.py`
  - `tests/live_runtime.py`
  - `tests/env-UT`, `tests/env-ST`, `tests/env-IT`, `tests/env-AT`, `tests/env-QT`
  - `tests/unit/helpers.py`
  - `tests/unit/UT1_17/test_ut1_17_metadata_enrichment.py`
  - `tests/local_runtime.py`

- Added missing documentation coverage across source:
  - `src/` docstring audit now returns `missing_docstrings=0`

- Added coverage closure tests:
  - `tests/unit/UT1_34/test_ut1_34_service_and_adapter_branches.py`
  - `tests/unit/UT1_35/test_ut1_35_coverage_closure.py`

---

## Integrity Gate Evidence

- ST/IT/AT anti-stub and anti-mock scan:
  - Command: `grep -R --line-number --exclude-dir='__pycache__' -E 'LocalIndexRuntime|local_service|tests\\.local_runtime|Mock|mock|stub|fake|local_mode=True' tests/system tests/integration tests/application tests/security`
  - Result: no matches

- Skip enforcement scan:
  - Command: `grep -R --line-number 'pytest\\.skip' tests/system tests/integration tests/application tests/security`
  - Result: no matches

- `/tmp` path scan in active code/test/scripts scope:
  - Command: `grep -R --line-number --exclude-dir='__pycache__' '/tmp' src tests scripts`
  - Result: no matches

---

## Residual Risk

- Live service stability can still introduce transient timeout failures; one AT preflight and one earlier full-suite pass attempt showed real endpoint `ReadTimeout`, and subsequent reruns passed cleanly.
