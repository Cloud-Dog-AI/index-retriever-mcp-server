# index-retriever-mcp-server — Context Summary

**Last updated:** 2026-02-20  
**Status:** Integrity remediation executed with evidence

---

## Verified Results

- Integrity verifier:
  - Command: `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
  - Result: `PASS: 10, FAIL: 0, WARN: 0`

- IT without Vault (must fail, not skip):
  - Command: `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT -q -rs`
  - Result: `12 errors`, explicit failure message `missing VAULT_TOKEN`, `0 skipped`

- Tiered test runs:
  - `python3 -m pytest tests/unit --env tests/env-UT -q -rs` → `49 passed`
  - `python3 -m pytest tests/system --env tests/env-ST -q -rs` → `12 passed`
  - `python3 -m pytest tests/integration --env tests/env-IT -q -rs` (with Vault sourced) → `12 passed`
  - `python3 -m pytest tests/application --env tests/env-AT -q -rs` (with Vault sourced) → `5 passed`
  - `python3 -m pytest tests/security --env tests/env-QT -q -rs` (with Vault sourced) → `5 passed`
  - `python3 -m pytest tests/contract --env tests/env-IT -q -rs` (with Vault sourced) → `3 passed`

- Full suite + coverage (Vault sourced):
  - Command: `python3 -m pytest tests/ --env tests/env-UT --env tests/env-ST --env tests/env-IT --env tests/env-AT --env tests/env-QT -q -rs --cov=src --cov-report=term-missing`
  - Result: `86 passed`
  - Coverage: `95%` (`1085 statements`, `53 missed`)

---

## Code and Test Corrections Applied

- `src/index_tools/config/loader.py`
  - Replaced invalid `cloud_dog_config.merge(...)` call with chained `cloud_dog_config.merger.deep_merge(...)`.

- `src/index_server/mcp_server.py`
  - Added explicit tool-category RBAC gating in `execute_tool(...)`.
  - Prevents `reader` role from calling ingest/admin/maintenance actions.

- `tests/conftest.py`
  - Live preflight remains hard-fail for live tiers when Vault/live deps are missing.
  - Added session teardown guard `live_service_cleanup_verification` that:
    - scans for orphaned run-prefix collections,
    - deletes any found,
    - fails the session if orphans were left behind.

- `tests/live_runtime.py`
  - Added deterministic run prefix for each test session.
  - Added run-prefix collection discovery helper.
  - Hardened `cleanup()` to delete by namespace prefix from backend listings, not only tracked collection set.

- `scripts/purge_chroma_test_collections.py`
  - Added one-off purge utility for historical orphan Chroma collections.
  - Supports `DRY_RUN=true|false` and configurable regex via `INDEX_RETRIEVER_CHROMA_PURGE_REGEX`.

- Unit coverage updates:
  - `tests/unit/UT1_31/test_ut1_31_server_runtime_paths.py`
  - `tests/unit/UT1_32/test_ut1_32_support_module_paths.py`
  - Added/adjusted assertions to align with real signatures/validation and RBAC behaviour.

---

## Live Backend Proof (CRU + External Verification)

With Vault sourced, CRU was executed via `cloud_dog_vdb` on all required backends, then externally verified:

- `chroma`:
  - External `curl` to collections endpoint returned `200`.
  - External `curl` to collection `count` endpoint confirmed stored record (`count_ok=True`).

- `qdrant`:
  - External `curl` to point endpoint returned `200`.
  - Payload contained expected `external_id`.

- `weaviate`:
  - External `curl` to object endpoint returned `200`.
  - Object ID matched expected deterministic UUID.

- `opensearch`:
  - External `curl` to `/{index}/_doc/{id}` returned `200`.
  - `_source.metadata.probe` confirmed updated value.

- `pgvector`:
  - External SQL verification via `psql` returned row `record_id:update`.

All probe collections were deleted after verification.

---

## Current Residual Risk

- No current integrity-gate failures were observed in the latest runs.
