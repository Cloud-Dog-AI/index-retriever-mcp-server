# index-retriever-mcp-server — Context Summary

**Last updated:** 2026-03-02  
**Status:** W15B-03 compliance lockdown verified (canonical loader + strict no-fallback identity checks + UT/ST/IT/AT pass)

---

## W15B-03 Compliance Lockdown Snapshot (2026-03-02)

- Instruction:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W15B-03-INDEX-RETRIEVER-COMPLIANCE-LOCKDOWN-STRICT.md`
- Canonical config loader proof:
  - `src/index_tools/config/loader.py` now includes canonical `cloud_dog_config.load_config(...)` path (`load_runtime_config`) with strict unresolved policy.
  - Mandatory check output: `config_loader_check=ok`.
- Local-docker live-provider contract alignment:
  - `tests/env-ST-local-docker`, `tests/env-IT-local-docker`, `tests/env-AT-local-docker`:
    - `CLOUD_DOG__INDEX__VDB__PROVIDER=qdrant`
    - `INDEX_RETRIEVER_LIVE_REQUIRED_PROVIDERS=qdrant`
  - Real runtime execution performed with Vault env sourced:
    - `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`
- Added strict no-fallback backend identity tests (ST/IT/AT):
  - `tests/system/ST1_13/test_st1_13_no_fallback_backend_identity.py`
  - `tests/integration/IT1_19/test_it1_19_no_fallback_backend_identity.py`
  - `tests/application/AT1_9/test_at1_9_no_fallback_backend_identity.py`
- Mandatory backend tier outcomes:
  - UT: `74 passed, 2 warnings`
  - ST: `13 passed`
  - IT: `19 passed`
  - AT: `10 passed`
- Evidence logs:
  - `/tmp/w15b03_index_ut.log`
  - `/tmp/w15b03_index_st.log`
  - `/tmp/w15b03_index_it.log`
  - `/tmp/w15b03_index_at.log`

---

## W14B-03 A2A Enablement + Auth Contract Snapshot (2026-03-01)

- Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14B-03-INDEX-RETRIEVER-A2A-ENABLE-AUTH-CONTRACT-STRICT.md`
- Runtime identity:
  - Container: `index-retriever-all`
  - Image: `index-retriever-local-docker-all-in-one:latest`
  - Image ID: `sha256:9cc4f10fc4802cc6bd387a0d058cb629180ed6c391718298385bdb618671bd29`
- A2A hard-stop precheck:
  - no auth: `/a2a/health` => `401`
  - `Authorization: Bearer 12345678`: `/a2a/health` => `200`
- Local runtime auth/env contract:
  - `TEST_A2A_API_KEY=12345678`
  - `CLOUD_DOG__INDEX__AUTH__API_KEYS=test-api-key,12345678`

Strict backend tiers:
- UT: `74 passed, 2 warnings`
- ST: `12 passed`
- IT: `18 passed`
- AT: `9 passed`

UI strict validation (`@cloud-dog/app-index-retriever`):
- lint/typecheck: `Tasks: 8 successful, 8 total`
- e2e: `12 passed`
- a11y: `2 passed`

Integrity + coverage:
- verify-test-integrity: `PASS: 10`, `FAIL: 0`, `WARN: 5`
- no-Vault IT: explicit `missing VAULT_TOKEN` failure (`18 errors`)
- full coverage: `TOTAL 1446 0 100%`, `123 passed`

---

## W14A-04 Route-Prefix + VDB Closeout Snapshot (2026-03-01)

- Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14A-04-INDEX-RETRIEVER-ROUTE-PFX-VDB-CLOSEOUT-STRICT.md`
- Canonical route contract active in test env keys:
  - `TEST_API_BASE_PATH=/app/v1`
  - `TEST_MCP_BASE_PATH=/mcp`
  - `TEST_WEB_BASE_PATH=/`
  - `TEST_A2A_BASE_PATH=/a2a`
- Runtime identity:
  - Container: `index-retriever-all`
  - Image: `index-retriever-local-docker-all-in-one:latest`
  - Image ID: `sha256:0648af633a50f7f59b1e7e6329e90e02836c97307e16adec4c94c20b63cb569c`
- VDB package evidence:
  - `/tmp/w14a04_index_vdb_version.log` => `0.4.1`

Strict backend tiers:
- UT: `71 passed, 2 warnings`
- ST: `12 passed`
- IT: `17 passed`
- AT: `8 passed`

Canonical route probes:
- `http://127.0.0.1:8686/app/v1/health` => HTTP 200
- `http://127.0.0.1:8687/mcp/tools` => HTTP 200 (`ok=true`, tools count `37`)
- `http://127.0.0.1:8687/tools` => HTTP 200 compatibility alias (`tools` count `37`)

UI strict validation (`@cloud-dog/app-index-retriever`):
- lint/typecheck: `Tasks: 8 successful, 8 total`
- e2e: `12 passed`
- a11y: `2 passed`

---

## W12C UI Validation Snapshot (2026-02-28)

- Runtime mode: local-docker (`tests/env-local-docker-server` -> `tests/env-IT-local-docker`)
- Runtime endpoints:
  - API: `http://127.0.0.1:8686`
  - MCP: `http://127.0.0.1:8687`
- Runtime image/hash:
  - Container ID: `631d636d7963f26a2dbf96ab058d7211300b1c0a77824b6d744eb0df2bd0ab37`
  - Container name: `index-retriever-all`
  - Image tag: `index-retriever-local-docker-all-in-one:latest`
  - Image ID: `sha256:937a3d17d6be3e253a03c1d74a517cd087a0587700ae07abea20c547cdc86f3f`
  - Runtime env hash: `2b5377ab75dd1510bed7c08f1ecc6d052b5243283dbffa0ac500a4dd5fa1fd0b`
- Mandatory capability gate checks before runtime tests:
  - local bind: `bind_local|ok`
  - API socket connect: `api_8686|ok`
  - MCP socket connect: `mcp_8687|ok`

Strict validation command results (`cloud-dog-ai-ui-monorepo`, app `@cloud-dog/app-index-retriever`):

- `npm run lint -- --filter=@cloud-dog/app-index-retriever` -> pass
- `npm run typecheck -- --filter=@cloud-dog/app-index-retriever` -> pass
- `npm run e2e -- --filter=@cloud-dog/app-index-retriever` -> `12 passed`, `0 failed`, `0 skipped`
- `npm run a11y -- --filter=@cloud-dog/app-index-retriever` -> `2 passed`, `0 failed`, `0 skipped`

Evidence artefacts:

- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-lint.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-typecheck.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-e2e.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-a11y.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/test-results/.last-run.json`
- `index-retriever-mcp-server/TESTS.md` section `W12C Execution Evidence (2026-02-28)`

---

## W12E UAT Readiness Snapshot (2026-03-01)

- Instruction: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W12E-03-INDEX-RETRIEVER-UAT-READY-SINGLE-DOCKER.md`
- Runtime contract validated:
  - Controller env: `tests/env-local-docker-server`
  - Runtime env: `tests/env-IT-local-docker`
  - API health: `http://127.0.0.1:8686/health` (HTTP 200, `status: ok`)
  - MCP tools: `http://127.0.0.1:8687/mcp/tools` (HTTP 200, `ok: true`)
- Runtime identity:
  - Container ID: `631d636d7963f26a2dbf96ab058d7211300b1c0a77824b6d744eb0df2bd0ab37`
  - Image tag: `index-retriever-local-docker-all-in-one:latest`
  - Image ID: `sha256:937a3d17d6be3e253a03c1d74a517cd087a0587700ae07abea20c547cdc86f3f`
  - Env hash: `2b5377ab75dd1510bed7c08f1ecc6d052b5243283dbffa0ac500a4dd5fa1fd0b`
- Capability checks before test execution:
  - `127.0.0.1:8686 CONNECT_OK`
  - `127.0.0.1:8687 CONNECT_OK`

Backend strict tiers (local-docker envs):

- `python3 -m pytest tests/unit/ --env tests/env-UT-local-docker -q` -> `61 passed, 2 warnings`
- `python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q` -> `12 passed`
- `python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q` -> `12 passed`
- `python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q` -> `7 passed`

UI strict validation (`@cloud-dog/app-index-retriever`):

- `npm run lint -- --filter=@cloud-dog/app-index-retriever` -> pass
- `npm run typecheck -- --filter=@cloud-dog/app-index-retriever` -> pass
- `npm run e2e -- --filter=@cloud-dog/app-index-retriever` -> `12 passed`, `0 failed`, `0 skipped`
- `npm run a11y -- --filter=@cloud-dog/app-index-retriever` -> `2 passed`, `0 failed`, `0 skipped`

Evidence paths:

- `index-retriever-mcp-server/TESTS.md` section `W12E UAT Readiness Evidence (2026-03-01, single-docker wave)`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-lint.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-typecheck.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-e2e.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-a11y.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/test-results/.last-run.json`

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
