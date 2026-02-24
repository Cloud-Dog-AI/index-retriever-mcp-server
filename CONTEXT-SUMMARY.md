# index-retriever-mcp-server — Context Summary

**Last updated:** 2026-02-24  
**Status:** W8C test-integrity and tool-hardening completed with evidence

---

## External Availability + Capability Checks

- Socket capability checks before live tiers:
  - `vdb1.app.vpc0.cloud-dog.net:6333 CONNECT_OK`
  - `llm1.cloud-dog.net:443 CONNECT_OK`
  - `vault0.cloud-dog.net:443 CONNECT_OK`
- Qdrant health:
  - `curl -sS http://vdb1.app.vpc0.cloud-dog.net:6333/healthz` → `healthz check passed`
- Embedding models:
  - `https://llm1.cloud-dog.net/api/tags` showed `bge-m3:567m`, `nomic-embed-text`, and `granite-embedding:278m` as available.
- Vault config:
  - `VAULT_SECTIONS channels,databases,email,idp,keys,models,redis,repository,storage,vdbs`
  - `VDB_CONFIGS chroma,opensearch,pgvector,qdrant,weaviate`

No permission/capability restriction (`PermissionError: [Errno 1] Operation not permitted`) was observed during these runs.

---

## Baseline Tier Results (Vault sourced)

Vault sourced with:
`set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`

- `python3 -m pytest tests/unit --env tests/env-UT -q -rs` → `61 passed`, `0 skipped`
- `python3 -m pytest tests/system --env tests/env-ST -q -rs` → `12 passed`, `0 skipped`
- `python3 -m pytest tests/contract --env tests/env-IT -q -rs` → `3 passed`, `0 skipped`
- `python3 -m pytest tests/integration --env tests/env-IT -q -rs` → `12 passed`, `0 skipped`
- `python3 -m pytest tests/application --env tests/env-AT -q -rs` → `6 passed`, `0 skipped`

No-vault failure proof:
- `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT -q -rs`
- Result: `12 errors`, explicit `missing VAULT_TOKEN`, `0 skipped`

---

## W8C Tool Verification (Transport Path)

- MCP tool catalogue via transport:
  - `python3 -m pytest tests/integration/IT1_6/ --env tests/env-IT -v -s --tb=long` → `1 passed`
  - Verified tools include: `admin_collection_create`, `ingest_text`, `search`.

- Tool execution via API transport:
  - `python3 -m pytest tests/integration/IT1_7/ --env tests/env-IT -v -s --tb=long` → `1 passed`
  - Verified:
    - `admin_collection_create` idempotency (double create)
    - `ingest_text -> search` pipeline on real VDB + real embedding
    - source metadata round-trip (`metadata.source == "test:w8c:step4"`)
    - collection isolation across two collections
    - cleanup via `admin_collection_delete`

---

## Code/Test Hardening Applied

- `tests/live_runtime.py`
  - Added source metadata round-trip field (`source`) alongside `source_uri`.
  - Added source-aware dedupe/reindex controls (`dedupe_policy`, `stale_after_days`, `indexing_signature`).
  - Added `ingest_reference(...)` for real file parse→index path.
  - Added collection admin/list methods for transport-level tool validation:
    - `collections_list(...)`
    - `admin_collection_delete(...)`
  - Added internal record-map cleanup on collection/filter/delete operations.

- `tests/system/ST1_5/test_st1_5.py`
  - Switched from inline text to real file-based `ingest_reference(...)` flow.

- `tests/application/AT1_1/test_at1_1.py`
  - Added explicit metadata completeness assertions and delete-by-metadata validation.

- `tests/application/AT1_2/test_at1_2.py`
  - Expanded to verify:
    - duplicate skip behaviour,
    - replace-on-content-change,
    - reindex on indexing signature change,
    - stale-age triggered reindex.

- `tests/integration/IT1_6/test_it1_6.py`
  - Updated to validate MCP catalogue via `/mcp/tools` transport path.

- `tests/integration/IT1_7/test_it1_7.py`
  - Updated to validate the 3 critical tools through `/api/v1/tools/{tool_name}` transport path.

- `src/index_server/mcp_server.py`
  - Normalised `ingest_text` tool return value to stable string `job_id` for transport clients.

- `REQUIREMENTS.md`
  - Added explicit FR requirement: ingest `source` must be preserved and returned in search metadata.

- `TESTS.md`
  - Updated environment usage, current run evidence, and IT tool-transport coverage descriptions.

---

## Integrity Gate Sequence (Current)

1. `bash ../cloud-dog-ai-platform-standards/migration/verify/verify-test-integrity.sh .`
   - `PASS: 10, FAIL: 0, WARN: 0`
2. No-vault IT run (must fail, not skip)
   - `12 errors`, explicit `missing VAULT_TOKEN`, `0 skipped`
3. Full tier run with Vault sourced
   - `61 UT + 12 ST + 12 IT + 6 AT + 5 QT + 3 CT = 99 passed`, `0 skipped`
4. Full coverage run with Vault sourced
   - `python3 -m pytest tests/ --env tests/env-UT --env tests/env-ST --env tests/env-IT --env tests/env-AT --env tests/env-QT -q -rs --cov=src --cov-report=term-missing`
   - `99 passed`, `0 failed`, `0 skipped`, `2 warnings`
   - `Coverage 100% (1123 statements, 0 missed)`

---

## Residual Risk

- Live endpoints can be slower on some runs; long-running AT/IT transport tests were observed, but completed successfully with no capability restrictions.
