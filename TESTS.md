# index-retriever-mcp-server — Test Plan

**Version:** 1.2  
**Date:** 2026-03-12  
**Standard:** PS-95  
**Latest verified tier run (W28A-133-F):** QT `31 passed`, UT `90 passed`, ST `17 passed`, IT `33 passed, 3 skipped`, AT `16 passed`

## Latest W23A Status (2026-03-06)

- Instruction file used:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W23A-INDEX-RETRIEVER-VDB-FULL-INTEGRATION.md`
- Added W23A matrix suites:
  - IT2.1-IT2.6: backend contract matrix (Chroma/Qdrant/OpenSearch/PGVector/Weaviate/Infinity)
  - IT2.7-IT2.12: parser provider matrix (DeepDoc/Docling/MinerU/Marker MCP/Transformers/Internal)
  - IT2.13: OCR-capable parser matrix
  - IT2.14: table extraction matrix
  - AT2.1-AT2.2: multi-backend consistency
  - AT2.3: multi-parser quality comparison
  - AT2.4: multi-embedding model comparison (BGE/Nomic/Granite)
  - AT2.5: full parser->chunk->index->search->retrieve E2E per backend
  - PT1.1-PT1.3: backend ingest baseline, backend search latency, parser throughput
- Added W23A env overlays:
  - `tests/env-VDB-chroma`
  - `tests/env-VDB-qdrant`
  - `tests/env-VDB-opensearch`
  - `tests/env-VDB-pgvector`
  - `tests/env-VDB-weaviate`
  - `tests/env-VDB-infinity`
  - `tests/env-PT`
- Exact W23A summary lines:
  - `7 passed, 7 skipped in 6.66s` (IT, `working/W23A-VDB-IT.log`)
  - `4 passed, 1 skipped in 41.93s` (AT, `working/W23A-VDB-AT.log`)
  - `2 passed, 1 skipped in 22.36s` (PT, `working/W23A-VDB-PT.log`)
- Skip classification for W23A:
  - Parser-provider coverage tests skip when provider endpoints/commands are not enabled/configured in env/Vault.
  - OCR/table/parser-throughput matrices skip when fewer than required parser providers are enabled.

W23A test ID map:

| ID | Tier | Path |
|---|---|---|
| IT2.1 | IT | `tests/integration/IT2_1/test_it2_1_chroma_contract.py` |
| IT2.2 | IT | `tests/integration/IT2_2/test_it2_2_qdrant_contract.py` |
| IT2.3 | IT | `tests/integration/IT2_3/test_it2_3_opensearch_contract.py` |
| IT2.4 | IT | `tests/integration/IT2_4/test_it2_4_pgvector_contract.py` |
| IT2.5 | IT | `tests/integration/IT2_5/test_it2_5_weaviate_contract.py` |
| IT2.6 | IT | `tests/integration/IT2_6/test_it2_6_infinity_contract.py` |
| IT2.7 | IT | `tests/integration/IT2_7/test_it2_7_deepdoc_parser.py` |
| IT2.8 | IT | `tests/integration/IT2_8/test_it2_8_docling_parser.py` |
| IT2.9 | IT | `tests/integration/IT2_9/test_it2_9_mineru_parser.py` |
| IT2.10 | IT | `tests/integration/IT2_10/test_it2_10_marker_parser.py` |
| IT2.11 | IT | `tests/integration/IT2_11/test_it2_11_transformers_parser.py` |
| IT2.12 | IT | `tests/integration/IT2_12/test_it2_12_internal_parser.py` |
| IT2.13 | IT | `tests/integration/IT2_13/test_it2_13_ocr_provider_matrix.py` |
| IT2.14 | IT | `tests/integration/IT2_14/test_it2_14_table_extraction_matrix.py` |
| AT2.1 | AT | `tests/application/AT2_1/test_at2_1_multi_backend_consistency_chroma_qdrant.py` |
| AT2.2 | AT | `tests/application/AT2_2/test_at2_2_multi_backend_consistency_pgvector_opensearch.py` |
| AT2.3 | AT | `tests/application/AT2_3/test_at2_3_multi_parser_quality_comparison.py` |
| AT2.4 | AT | `tests/application/AT2_4/test_at2_4_multi_embedding_models.py` |
| AT2.5 | AT | `tests/application/AT2_5/test_at2_5_full_pipeline_e2e_per_backend.py` |
| PT1.1 | PT | `tests/parser/PT1_1/test_pt1_1_backend_ingest_baseline.py` |
| PT1.2 | PT | `tests/parser/PT1_2/test_pt1_2_backend_search_latency.py` |
| PT1.3 | PT | `tests/parser/PT1_3/test_pt1_3_parser_throughput_comparison.py` |

## Latest W15B-03 Status (2026-03-02)

- Instruction file used:
  - `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W15B-03-INDEX-RETRIEVER-COMPLIANCE-LOCKDOWN-STRICT.md`
- Canonical loader check:
  - `python3 - <<'PY' ... assert 'load_config(' in src/index_tools/config/loader.py ... PY`
  - Result: `config_loader_check=ok`
- Loader/runtime compliance updates:
  - `src/index_tools/config/loader.py` now contains canonical `cloud_dog_config.load_config(...)` path via `load_runtime_config(...)` with strict unresolved policy.
  - Backward compatibility preserved for layer-merge unit path when explicit layers are provided.
- Live runtime provider contract for local-docker strict tiers:
  - `tests/env-ST-local-docker`, `tests/env-IT-local-docker`, `tests/env-AT-local-docker`
    - `CLOUD_DOG__INDEX__VDB__PROVIDER=qdrant`
    - `INDEX_RETRIEVER_LIVE_REQUIRED_PROVIDERS=qdrant`
  - Required Vault env sourced for ST/IT/AT runs:
    - `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`
- Added strict no-fallback identity tests:
  - `tests/system/ST1_13/test_st1_13_no_fallback_backend_identity.py`
  - `tests/integration/IT1_19/test_it1_19_no_fallback_backend_identity.py`
  - `tests/application/AT1_9/test_at1_9_no_fallback_backend_identity.py`

Exact strict backend summary lines:

- `74 passed, 2 warnings in 1.50s` (UT, `/tmp/w15b03_index_ut.log`)
- `13 passed in 11.86s` (ST, `/tmp/w15b03_index_st.log`)
- `19 passed in 11.86s` (IT, `/tmp/w15b03_index_it.log`)
- `10 passed in 11.58s` (AT, `/tmp/w15b03_index_at.log`)

## Latest W14B-03 Status (2026-03-01)

- Instruction file used: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14B-03-INDEX-RETRIEVER-A2A-ENABLE-AUTH-CONTRACT-STRICT.md`
- Runtime image + hash:
  - `index-retriever-local-docker-all-in-one`
  - `sha256:9cc4f10fc4802cc6bd387a0d058cb629180ed6c391718298385bdb618671bd29`
- A2A env/auth contract keys applied in active local runtime env files:
  - `TEST_A2A_API_KEY=12345678`
  - `CLOUD_DOG__INDEX__AUTH__API_KEYS=test-api-key,12345678`

Hard-stop precheck evidence:

- initial baseline (before fix): `/a2a/health` returned `404` (no-auth and auth), captured in strict precheck shell output prior to implementation
- post-fix strict precheck:
  - no-auth: `401` (`/tmp/w14b03_index_a2a_noauth.code`)
  - `Authorization: Bearer 12345678`: `200` (`/tmp/w14b03_index_a2a_auth.code`)
  - `/tmp/w14b03_index_a2a_noauth.json` -> `{"detail":"Authentication failed"}`
  - `/tmp/w14b03_index_a2a_auth.json` -> `{"status":"ok", ...}`

Exact strict backend summary lines:

- `74 passed, 2 warnings in 1.34s` (UT, `/tmp/w14b03_index_ut.log`)
- `12 passed in 9.59s` (ST, `/tmp/w14b03_index_st.log`)
- `18 passed in 9.22s` (IT, `/tmp/w14b03_index_it.log`)
- `9 passed in 9.25s` (AT, `/tmp/w14b03_index_at.log`)

Exact WebUI strict summary lines:

- `Tasks: 8 successful, 8 total` (lint, `/tmp/w14b03_index_ui_lint.log`)
- `Tasks: 8 successful, 8 total` (typecheck, `/tmp/w14b03_index_ui_typecheck.log`)
- `12 passed (25.8s)` (e2e, `/tmp/w14b03_index_ui_e2e.log`)
- `2 passed (13.4s)` (a11y, `/tmp/w14b03_index_ui_a11y.log`)

Integrity + coverage evidence:

- `verify-test-integrity.sh` -> `PASS: 10`, `FAIL: 0`, `WARN: 5` (`/tmp/w14b03_index_verify_test_integrity.log`)
- no-Vault IT fail-closed check -> explicit `missing VAULT_TOKEN`, `18 errors` (`/tmp/w14b03_index_it_no_vault.log`)
- full tier coverage -> `TOTAL 1446 0 100%`, `123 passed` (`/tmp/w14b03_index_cov.log`)

---

## Latest W14A-04 Status (2026-03-01)

- Instruction file used: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W14A-04-INDEX-RETRIEVER-ROUTE-PFX-VDB-CLOSEOUT-STRICT.md`
- Route-prefix env contract applied across active env files:
  - `TEST_API_BASE_PATH=/app/v1`
  - `TEST_MCP_BASE_PATH=/mcp`
  - `TEST_WEB_BASE_PATH=/`
  - `TEST_A2A_BASE_PATH=/a2a`
- Runtime image + hash:
  - `index-retriever-local-docker-all-in-one`
  - `sha256:0648af633a50f7f59b1e7e6329e90e02836c97307e16adec4c94c20b63cb569c`
- `cloud_dog_vdb` runtime version evidence:
  - `/tmp/w14a04_index_vdb_version.log` -> `0.4.1`

Exact strict backend summary lines:

- `71 passed, 2 warnings in 1.58s` (UT, `/tmp/w14a04_index_ut.log`)
- `12 passed in 11.19s` (ST, `/tmp/w14a04_index_st.log`)
- `17 passed in 9.12s` (IT, `/tmp/w14a04_index_it.log`)
- `8 passed in 8.90s` (AT, `/tmp/w14a04_index_at.log`)

Route probe outputs:

- canonical API health: `curl -fsS http://127.0.0.1:8686/app/v1/health` -> HTTP 200 (`/tmp/w14a04_index_health_canonical.json`)
- canonical MCP tools: `curl -fsS http://127.0.0.1:8687/mcp/tools` -> HTTP 200, `ok=true`, `tools=37` (`/tmp/w14a04_index_tools_canonical.json`)
- legacy MCP alias: `curl -fsS http://127.0.0.1:8687/tools` -> HTTP 200, compatibility alias (`/tmp/w14a04_index_tools_legacy_alias.json`, `tools=37`)

Exact WebUI strict summary lines:

- `Tasks: 8 successful, 8 total` (lint, `/tmp/w14a04_index_ui_lint.log`)
- `Tasks: 8 successful, 8 total` (typecheck, `/tmp/w14a04_index_ui_typecheck.log`)
- `12 passed (25.8s)` (e2e, `/tmp/w14a04_index_ui_e2e.log`)
- `2 passed (13.4s)` (a11y, `/tmp/w14a04_index_ui_a11y.log`)

---

## Latest W13B Status (2026-03-01)

- Instruction file used: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W13B-INDEX-RETRIEVER-VDB-0.4.1-ADOPTION-STRICT.md`
- Runtime env/controller env files used:
  - `tests/env-local-docker-server`
  - `tests/env-UT-local-docker`
  - `tests/env-ST-local-docker`
  - `tests/env-IT-local-docker`
  - `tests/env-AT-local-docker`
  - `tests/env-QT-local-docker`
- Runtime image + hash:
  - `index-retriever-local-docker-all-in-one`
  - `sha256:4dabd651208252abd5dc0bd743687dd3ace7b74bb85f6f29f09b835dbe2e2766`
- Capability gate checks:
  - `CONNECT_OK 127.0.0.1:8686`
  - `CONNECT_OK 127.0.0.1:8687`
  - `CONNECT_OK llm1.cloud-dog.net:443`

Exact backend strict summary lines:

- `71 passed, 2 warnings in 1.39s` (UT, `/tmp/w13b_idx_ut.log`)
- `12 passed in 10.21s` (ST, `/tmp/w13b_idx_st.log`)
- `4 passed in 4.22s` (CT, `/tmp/w13b_idx_ct.log`)
- `17 passed in 9.34s` (IT, `/tmp/w13b_idx_it.log`)
- `8 passed in 9.33s` (AT, `/tmp/w13b_idx_at.log`)
- `6 passed in 2.30s` (QT, `/tmp/w13b_idx_qt.log`)

Exact WebUI strict summary lines:

- `Tasks: 8 successful, 8 total` (lint, `/tmp/w13b_idx_ui_lint.log`)
- `Tasks: 8 successful, 8 total` (typecheck, `/tmp/w13b_idx_ui_typecheck.log`)
- `12 passed (25.8s)` (e2e, `/tmp/w13b_idx_ui_e2e.log`)
- `2 passed (13.4s)` (a11y, `/tmp/w13b_idx_ui_a11y.log`)

Coverage evidence:

- `python3 -m pytest tests/ --env tests/env-UT-local-docker --env tests/env-ST-local-docker --env tests/env-IT-local-docker --env tests/env-AT-local-docker --env tests/env-QT-local-docker -q -rs --cov=src --cov-report=term-missing`
- Result: `118 passed, 2 warnings`, `TOTAL 1383 0 100%` (`/tmp/w13b_idx_cov.log`)

W13B added/updated test IDs:

| ID | Tier | Coverage intent |
|----|------|------------------|
| IT1.13 | IT | Metadata round-trip: `source_uri`, `filename`, `mime_type` |
| IT1.14 | IT | Capability-aware planning and unsupported-filter failure path |
| IT1.15 | IT | Infinity backend path / strict blocked behavior when unavailable |
| IT1.16 | IT | Delegation boundary through `cloud_dog_vdb` parser/OCR/table path |
| IT1.17 | IT | MCP/API execution coverage for wrapper tools |
| CT1.4 | CT | Infinity adapter contract coverage |
| AT1.7 | AT | Multi-profile cross-backend metadata parity invariants |
| QT1.6 | QT | Provider diagnostic envelope explicit + secret-safe |

---

## Latest W11D Status (2026-02-28)

- Instruction file used: `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W11D-03-INDEX-RETRIEVER-LOCAL-DOCKER-IT-AT-STRICT.md`
- Runtime env/controller env files used:
  - `tests/env-local-docker-server`
  - `tests/env-IT-local-docker`
  - `tests/env-AT-local-docker`
- Runtime image + hash:
  - `index-retriever-local-docker-all-in-one`
  - `sha256:937a3d17d6be3e253a03c1d74a517cd087a0587700ae07abea20c547cdc86f3f`
- Exact commands run:
  - `bash local-docker-server.sh --env tests/env-local-docker-server ensure`
  - `curl -fsS http://127.0.0.1:8686/health >/tmp/w11d_index_health_api.json`
  - `curl -fsS http://127.0.0.1:8687/mcp/tools >/tmp/w11d_index_tools.json`
  - `python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q`
  - `python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q`
  - `python3 -m pytest tests/application/AT1_1 --env tests/env-AT-local-docker -q`
- Exact summary lines:
  - `12 passed in 7.98s`
  - `7 passed in 7.22s`
  - `1 passed in 1.67s`
- Evidence report path: `working/W11D-P3-INDEX-LOCAL-DOCKER-IT-AT-REPORT-2026-02-27.md`
- Current status: `COMPLETE VERIFIED`

---

## Environment Requirements

### Vault (live tiers)
```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
```

### Env files
- `tests/env-UT`
- `tests/env-ST`
- `tests/env-IT`
- `tests/env-AT`
- `tests/env-QT`

Required route-prefix keys in active env files:
- `TEST_API_BASE_PATH`
- `TEST_MCP_BASE_PATH`
- `TEST_WEB_BASE_PATH`
- `TEST_A2A_BASE_PATH`
- `TEST_A2A_API_KEY`
- `CLOUD_DOG__INDEX__AUTH__API_KEYS`

### External services (IT/AT/QT)
- PostgreSQL (profiles, jobs, audit metadata)
- Chroma (local or remote)
- Qdrant, OpenSearch, Weaviate, PGVector (for contract tests, optional per backend)
- Embedding provider (Ollama on llm1/llm2, or OpenAI-compat endpoint)

---

## Latest Verified Runs (2026-02-24)

- Baseline socket capability checks before each live tier:
  - `vdb1.app.vpc0.cloud-dog.net:6333 CONNECT_OK`
  - `llm1.cloud-dog.net:443 CONNECT_OK`
- External availability:
  - `curl http://vdb1.app.vpc0.cloud-dog.net:6333/healthz` → `healthz check passed`
  - `https://llm1.cloud-dog.net/api/tags` → `bge-m3:567m AVAILABLE`, `nomic-embed-text AVAILABLE`, `granite-embedding:278m AVAILABLE`
- Vault-less IT proof:
  - `env -u VAULT_TOKEN -u VAULT_ADDR -u VAULT_NAMESPACE -u CLOUD_DOG__VAULT__TOKEN python3 -m pytest tests/integration --env tests/env-IT -q -rs`
  - Result: `12 errors`, explicit `missing VAULT_TOKEN`, `0 skipped`
- Tier results with Vault sourced:
  - `python3 -m pytest tests/unit --env tests/env-UT -q -rs` → `61 passed, 0 skipped`
  - `python3 -m pytest tests/system --env tests/env-ST -q -rs` → `12 passed, 0 skipped`
  - `python3 -m pytest tests/contract --env tests/env-IT -q -rs` → `3 passed, 0 skipped`
  - `python3 -m pytest tests/integration --env tests/env-IT -q -rs` → `12 passed, 0 skipped`
  - `python3 -m pytest tests/application --env tests/env-AT -q -rs` → `6 passed, 0 skipped`
  - `python3 -m pytest tests/security --env tests/env-QT -q -rs` → `5 passed, 0 skipped`
- Full suite + coverage:
  - `python3 -m pytest tests/ --env tests/env-UT --env tests/env-ST --env tests/env-IT --env tests/env-AT --env tests/env-QT -q -rs --cov=src --cov-report=term-missing`
  - Result: `99 passed, 0 failed, 0 skipped` (2 warnings), `Coverage 100% (1123/1123)`

---

## Unit Tests (UT) — 43 tests

Mocking allowed. No external services required.

| ID | Test | Module | Description |
|----|------|--------|-------------|
| UT1.1 | ConfigLoaderPrecedence | `index_tools/config/` | Config loads with correct precedence: env → .env → YAML → defaults |
| UT1.2 | ConfigVaultIntegration | `index_tools/config/` | Vault secrets merged into config via `cloud_dog_config` |
| UT1.3 | ConfigValidation | `index_tools/config/` | Invalid config rejected with clear error messages |
| UT1.4 | ProfileModelValidation | `index_tools/config/` | Profile Pydantic models validate all required fields |
| UT1.5 | RBACPolicyEval | `index_tools/security/` | `cloud_dog_idam` RBAC correctly evaluates subject/object/action |
| UT1.6 | ConnectorScopeEnforcement | `index_tools/security/` | Filesystem scope blocks access outside allowed roots |
| UT1.7 | AuditEventShape | `index_tools/audit/` | Audit events include required fields |
| UT1.8 | AuditRedaction | `index_tools/audit/` | Secrets are redacted from audit entries |
| UT1.9 | ConnectorFilesystemResolve | `index_tools/connectors/` | Filesystem connector resolves paths within scope |
| UT1.10 | ConnectorS3Resolve | `index_tools/connectors/` | S3 connector builds correct fetch plan |
| UT1.11 | ConnectorWebDAVResolve | `index_tools/connectors/` | WebDAV connector builds correct fetch plan |
| UT1.12 | ConvertRegistrySelection | `index_tools/convert/` | Converter registry selects best backend for file type |
| UT1.13 | ConvertPDFExtract | `index_tools/convert/` | PDF conversion extracts text correctly |
| UT1.14 | ConvertOfficeExtract | `index_tools/convert/` | Office document conversion extracts text correctly |
| UT1.15 | ChunkingTokenStrategy | `index_tools/pipeline/` | Token-based chunking produces correct chunk sizes |
| UT1.16 | ChunkingOverlap | `index_tools/pipeline/` | Chunk overlap is applied correctly |
| UT1.17 | MetadataEnrichment | `index_tools/pipeline/` | Metadata includes all required fields (source, hash, timestamps) |
| UT1.18 | DedupeHashDetection | `index_tools/pipeline/` | Duplicate detected by SHA-256 fingerprint |
| UT1.19 | DedupeSizeMtimeDetection | `index_tools/pipeline/` | Duplicate detected by size + mtime |
| UT1.20 | DedupePolicySkip | `index_tools/pipeline/` | Skip policy prevents re-ingestion |
| UT1.21 | DedupePolicyReplace | `index_tools/pipeline/` | Replace policy updates existing document |
| UT1.22 | DedupePolicyVersion | `index_tools/pipeline/` | Version policy creates linked document |
| UT1.23 | EmbeddingRegistryLookup | `index_tools/embeddings/` | Provider registry returns correct adapter for profile |
| UT1.24 | VDBRegistryLookup | `index_tools/vdb/` | Backend registry returns correct adapter for profile |
| UT1.25 | SearchQueryNormalisation | `index_tools/search/` | Query normalisation produces consistent output |
| UT1.26 | SearchFilterValidation | `index_tools/search/` | Metadata filters validated before query |
| UT1.27 | JobModelValidation | `index_tools/queue/` | Job models validate via `cloud_dog_jobs` |
| UT1.28 | IdempotencyKeyGeneration | `index_tools/queue/` | Idempotency key generated deterministically |
| UT1.29 | ToolDefinitionSchemas | `index_tools/tools/` | All tool Pydantic schemas validate correctly |
| UT1.30 | PipelineProgressEvents | `index_tools/pipeline/` | Pipeline emits progress events at each stage |

### Additional Unit Coverage (UT1.31–UT1.43)

| ID | Test | Description | Traces To |
|----|------|-------------|-----------|
| UT1.31 | ServerRuntimePaths | API/MCP runtime path, app construction, and startup branch coverage | FR-01, FR-01A |
| UT1.32 | SupportModulePaths | Connectors, converters, lifecycle, queue, audit, RBAC helper branch coverage | FR-08, FR-09, FR-10 |
| UT1.33 | ServiceBranchPaths | Service profile/document/job/cleanup control-path coverage | FR-03, FR-07, FR-16 |
| UT1.34 | ServiceAndAdapterBranches | Service + adapter behavior across delete/search/filter pathways | FR-11, FR-14, FR-16 |
| UT1.35 | CoverageClosure | API/MCP/auth/support closure paths and error mapping coverage | FR-01, FR-04, FR-17 |
| UT1.36 | ServiceVDBBranches | cloud_dog_vdb delegation and diagnostic envelope branch coverage | FR-13, FR-13A, FR-13B |
| UT1.37 | MCPVDBDispatch | MCP dispatch coverage for cloud_dog_vdb wrapper tools | FR-13A, FR-13B |
| UT1.38 | A2AAuthContract | `/a2a` auth parity and API-key contract behavior | FR-01B, FR-04 |
| UT1.39 | RuntimeConfigLoaderPaths | Canonical cloud_dog_config runtime loader path coverage | FR-02 |
| UT1.40 | DatabaseAbstraction | cloud_dog_db engine/session abstraction tests | R-DB-01, R-DB-02, R-DB-03 |
| UT1.41 | FTPConnector | FTP fetch-plan parsing and connection/auth/not-found error mapping | FR-08, FR-09 |
| UT1.42 | GDriveConnector | Google Drive reference parsing and HTTP auth/not-found error mapping | FR-08, FR-09 |
| UT1.43 | EmbeddingDimensionValidation | Enforces embedding dimension consistency and mismatch rejection | R-EMBED-02 |

---

## System Tests (ST) — 12 tests

Real DB and VDB required. No mocking of backends.

| ID | Test | Description |
|----|------|-------------|
| ST1.1 | ProfileCreatePersist | Create profile via admin; verify persisted to DB |
| ST1.2 | CollectionCreateDelete | Create and delete collection on Chroma backend |
| ST1.3 | IngestUploadPipeline | Upload file → convert → chunk → embed → upsert; verify chunks in VDB |
| ST1.4 | IngestTextPipeline | Ingest raw text → chunk → embed → upsert; verify chunks |
| ST1.5 | IngestReferencePipeline | Ingest filesystem reference → fetch → convert → index |
| ST1.6 | SearchTopK | Search returns top_k results with correct scores |
| ST1.7 | SearchMetadataFilter | Search with metadata filter returns only matching documents |
| ST1.8 | DeleteByID | Delete document by ID; verify removed from VDB and metadata DB |
| ST1.9 | DeleteByFilter | Delete by metadata filter; verify correct documents removed |
| ST1.10 | RetentionCleanup | Retention job removes old documents per policy |
| ST1.11 | JobEnqueueExecute | Job enqueued via `cloud_dog_jobs`; worker executes ingest pipeline |
| ST1.12 | AuditLogPersistence | Audit events persisted to JSONL file with correct format |

---

## Integration Tests (IT) — 14 tests

Real services required. Tests cross-component interaction.

| ID | Test | Description | Services |
|----|------|-------------|----------|
| IT1.1 | APIHealthEndpoint | `GET /health` returns status with DB/VDB/embedding checks | FastAPI |
| IT1.2 | APIAuthReject | Unauthenticated request returns 401 | FastAPI + `cloud_dog_idam` |
| IT1.3 | APIAuthAccept | Valid API key/JWT grants access | FastAPI + `cloud_dog_idam` |
| IT1.4 | APIRBACIngestGating | Reader role cannot ingest; writer role can | FastAPI + `cloud_dog_idam` |
| IT1.5 | APIRBACAdminGating | Non-admin cannot create profiles | FastAPI + `cloud_dog_idam` |
| IT1.6 | MCPToolCatalogue | MCP transport `/mcp/tools` includes `admin_collection_create`, `ingest_text`, and `search` | MCP transport |
| IT1.7 | MCPToolExecution | API tool transport validates collection create idempotency, ingest→search source round-trip, and collection isolation | API transport + VDB + embedding |
| IT1.8 | CorrelationIDPropagation | Correlation ID propagates through logs and audit | FastAPI + `cloud_dog_logging` |
| IT1.9 | ChromaContractTest | All CRUD operations pass against Chroma | `cloud_dog_vdb` + Chroma |
| IT1.10 | QdrantContractTest | All CRUD operations pass against Qdrant | `cloud_dog_vdb` + Qdrant |
| IT1.11 | EmbeddingProviderOllama | Embedding via Ollama returns correct dimension vectors | `cloud_dog_llm` + Ollama |
| IT1.12 | StreamingIngestSSE | SSE ingest stream indexes events in order | FastAPI + SSE + VDB |
| IT1.20 | JobManagementTools | `job_list`, `job_cancel`, `job_retry`, `queue_status` contract and schema checks | FR-07 |
| IT1.21 | CollectionRBAC | Collection-level role ACL enforced for authorized vs unauthorized calls | FR-05 |

---

## Application Tests (AT) — core and extended workflow tests

End-to-end user workflows.

| ID | Test | Description |
|----|------|-------------|
| AT1.1 | FullWorkflow_UploadSearchRetrieve | Upload file → wait for job → search → retrieve chunks → verify content |
| AT1.2 | FullWorkflow_DeduplicateSkip | Duplicate skip, replace-on-change, and stale-triggered reindex behaviours |
| AT1.3 | FullWorkflow_ProfileCollectionLifecycle | Admin creates profile → creates collection → ingests → searches → deletes collection |
| AT1.4 | FullWorkflow_RetentionEnforcement | Ingest documents → run retention with age policy → verify old docs removed |
| AT1.5 | FullWorkflow_MultiBackendSwitch | Create two profiles (Chroma, Qdrant) → ingest to both → search both → same contract |
| AT1.6 | RuntimeMatrix_API_MCP_Transport | Local-docker/remote-runtime API + MCP transport workflow with live endpoints |
| AT1.10 | AdminWebUIPlaywright | Browser-driven admin WebUI CRUD for profiles, users, groups, and API keys with RBAC denial verification |

---

## Quality Tests (QT) — 5 tests

Security and quality checks.

| ID | Test | Description |
|----|------|-------------|
| QT1.1 | SecretsNeverLogged | Grep audit and ops logs; no API keys, tokens, or passwords present |
| QT1.2 | ConnectorScopeEscape | Filesystem connector blocks path traversal outside configured roots |
| QT1.3 | NonAdminCannotCreateProfile | Non-admin attempt to create profile returns 403 |
| QT1.4 | UKEnglishCompliance | All source files, docs, and error messages use UK English |
| QT1.5 | BackendContractConformance | All enabled VDB backends pass identical contract test suite |

---

## Test Execution

```bash
# Load Vault
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a

# Unit tests (no external services)
pytest tests/unit/ --env tests/env-UT -v

# System tests (requires DB + Chroma)
pytest tests/system/ --env tests/env-ST -v

# Contract tests (requires VDB backends)
pytest tests/contract/ --env tests/env-IT -v

# Integration tests (requires running API server + VDB + embedding)
pytest tests/integration/ --env tests/env-IT -v

# Application tests (full stack)
pytest tests/application/ --env tests/env-AT -v

# Quality tests
pytest tests/security/ --env tests/env-QT -v

# All tests
pytest tests/ --env tests/env-UT --env tests/env-ST --env tests/env-IT --env tests/env-AT --env tests/env-QT -v --cov=src/
```

---

## Runtime Matrix Evidence (2026-02-27, local-docker)

- Runtime controller: `./local-docker-server.sh --env tests/env-local-docker-server`
- Runtime env source: `tests/env-IT-local-docker`
- Runtime container/image: `index-retriever-all` / `index-retriever-local-docker-all-in-one` (`sha256:937a3d17d6be...`)
- Code revision under test: `ae460a1`

Prerequisite for live integration/application runs:

- `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`

Commands executed:

- `python3 -m pytest tests/integration/IT1_1 --env tests/env-IT-local-docker -q` -> `1 passed` (with Vault env sourced)
- `python3 -m pytest tests/application/AT1_1 --env tests/env-AT-local-docker -q` -> `1 passed` (with Vault env sourced)

## W11D Strict Local-Docker IT/AT Evidence (2026-02-27)

- Vault sourced:
  - `set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a`
- Runtime ensure:
  - `bash local-docker-server.sh --env tests/env-local-docker-server ensure`
  - Result: `ALREADY RUNNING with matching env`
- Endpoint prechecks:
  - `curl -fsS http://127.0.0.1:8686/health >/tmp/w11d_index_health_api.json`
  - `curl -fsS http://127.0.0.1:8687/mcp/tools >/tmp/w11d_index_tools.json`
  - `/tmp/w11d_index_health_api.json` SHA256: `6d743e7ccfa94a025e1e81d6f1490593a9b10d7456de81d10238d1e1d93cf636`
  - `/tmp/w11d_index_tools.json` SHA256: `d8a8d749e815fbccf74da3cdc8b9853243041cfa1bc12b29240626697b7b1aee`
- Runtime image/hash:
  - Container: `631d636d7963`
  - Image: `index-retriever-local-docker-all-in-one`
  - Image ID: `sha256:937a3d17d6be3e253a03c1d74a517cd087a0587700ae07abea20c547cdc86f3f`
  - Env hash: `2b5377ab75dd1510bed7c08f1ecc6d052b5243283dbffa0ac500a4dd5fa1fd0b`
- Strict command outcomes:
  - `python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q` -> `12 passed`
  - `python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q` -> `7 passed`
- `python3 -m pytest tests/application/AT1_1 --env tests/env-AT-local-docker -q` -> `1 passed`
- Final accumulator: `W11D_EXIT_CODE=0`

---

## Web UI + A2A Traceability (UI-P5-IDX-TST)

Target app: in-repo Admin WebUI served from `/admin/ui/*` by `index-retriever-mcp-server`  
Execution mode: Playwright browser AT against a real HTTP API runtime; WebUI is API-only client.

| UI Test ID | Requirement Mapping | Playwright Spec File | Test Type | Expected Outcome |
|---|---|---|---|---|
| UI-IT1.1 | FR-01, FR-17 | `apps/index-retriever/tests/e2e/health-auth.spec.ts` | IT | API health/auth and initial console readiness |
| UI-IT1.2 | FR-03, FR-16, FR-17 | `apps/index-retriever/tests/e2e/profile-crud.spec.ts` | IT | Runtime profile CRUD and validation error mapping |
| UI-IT1.3 | FR-16, FR-17 | `apps/index-retriever/tests/e2e/collection-crud.spec.ts` | IT | Collection lifecycle operations mapped to API |
| UI-IT1.4 | FR-01, FR-14 | `apps/index-retriever/tests/e2e/mcp-catalogue-and-tool-call.spec.ts` | IT | MCP catalogue exposure and tool execution panel |
| UI-IT1.5 | FR-06, FR-17 | `apps/index-retriever/tests/e2e/audit-job-health-observability.spec.ts` | IT | Audit/log/job/health views and correlation IDs |
| UI-AT1.1 | FR-08, FR-09, FR-10 | `apps/index-retriever/tests/e2e/upload-index-search.spec.ts` | AT | Upload -> index -> search -> retrieve full workflow |
| UI-AT1.2 | FR-11, FR-14 | `apps/index-retriever/tests/e2e/dedupe-and-reindex.spec.ts` | AT | Dedupe and reindex workflow with deterministic outcomes |
| UI-AT1.3 | FR-13, FR-16 | `apps/index-retriever/tests/e2e/multi-backend-profile-switch.spec.ts` | AT | Profile/backend switch workflow behaves consistently |
| UI-AT1.4 | FR-16, FR-17 | `apps/index-retriever/tests/e2e/retention-and-delete-controls.spec.ts` | AT | Retention/delete actions require confirmation and succeed |
| UI-AT1.5 | NFR WebUI usability/accessibility | `apps/index-retriever/tests/a11y.spec.ts` | AT/a11y | Zero critical accessibility violations on core routes |
| UI-AT1.6 | CFG-07, CFG-11, CFG-13 | `tests/application/AT1_10/test_at1_10_admin_webui_playwright.py` | AT | Browser CRUD for profiles, users, groups, and API keys with admin/reader RBAC verification |

Strict command set (when app is implemented):

```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever
npm run typecheck -- --filter=@cloud-dog/app-index-retriever
npm run e2e -- --filter=@cloud-dog/app-index-retriever
npm run a11y -- --filter=@cloud-dog/app-index-retriever
```

### W12C Execution Evidence (2026-02-28)

Runtime and capability gates (real runtime; no mocks/stubs):

- Runtime ensure command used by Playwright webServer:
  - `cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server && bash local-docker-server.sh --env tests/env-local-docker-server ensure`
- Runtime env chain:
  - Control env: `tests/env-local-docker-server`
  - Source runtime env: `tests/env-IT-local-docker`
  - API endpoint: `http://127.0.0.1:8686`
  - MCP endpoint: `http://127.0.0.1:8687`
- Mandatory socket/network capability checks before test execution:
  - `bind_local|ok`
  - `api_8686|ok`
  - `mcp_8687|ok`

Strict command outcomes (exact commands executed):

```bash
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever
npm run typecheck -- --filter=@cloud-dog/app-index-retriever
npm run e2e -- --filter=@cloud-dog/app-index-retriever
npm run a11y -- --filter=@cloud-dog/app-index-retriever
```

- `npm run lint -- --filter=@cloud-dog/app-index-retriever`
  - Result: PASS (`Tasks: 8 successful, 8 total`; failed tasks: 0)
- `npm run typecheck -- --filter=@cloud-dog/app-index-retriever`
  - Result: PASS (`Tasks: 8 successful, 8 total`; failed tasks: 0)
- `npm run e2e -- --filter=@cloud-dog/app-index-retriever`
  - Result: PASS (`12 passed (25.8s)`, `0 failed`, `0 skipped`)
- `npm run a11y -- --filter=@cloud-dog/app-index-retriever`
  - Result: PASS (`2 passed (13.4s)`, `0 failed`, `0 skipped`)

Evidence artefacts:

- Turbo logs:
  - `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-lint.log`
  - `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-typecheck.log`
  - `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-e2e.log`
  - `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-a11y.log`
- Playwright run state:
  - `cloud-dog-ai-ui-monorepo/apps/index-retriever/test-results/.last-run.json`

### W12E UAT Readiness Evidence (2026-03-01, single-docker wave)

Instruction file:

- `cloud-dog-ai-platform-standards/working/AGENT-INSTRUCTION-W12E-03-INDEX-RETRIEVER-UAT-READY-SINGLE-DOCKER.md`

Required runtime contract (validated):

- Control env: `tests/env-local-docker-server`
- Runtime env: `tests/env-IT-local-docker`
- Health: `http://127.0.0.1:8686/health` -> HTTP 200 with `status: ok`
- MCP tools: `http://127.0.0.1:8687/mcp/tools` -> HTTP 200 with `ok: true`

Mandatory sequence command lines executed:

```bash
bash local-docker-server.sh --env tests/env-local-docker-server ensure
curl -fsS http://127.0.0.1:8686/health
curl -fsS http://127.0.0.1:8687/mcp/tools
python3 -m pytest tests/unit/ --env tests/env-UT-local-docker -q
python3 -m pytest tests/system/ --env tests/env-ST-local-docker -q
python3 -m pytest tests/integration/ --env tests/env-IT-local-docker -q
python3 -m pytest tests/application/ --env tests/env-AT-local-docker -q
cd /opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo
npm run lint -- --filter=@cloud-dog/app-index-retriever
npm run typecheck -- --filter=@cloud-dog/app-index-retriever
npm run e2e -- --filter=@cloud-dog/app-index-retriever
npm run a11y -- --filter=@cloud-dog/app-index-retriever
```

Exact backend summary lines (final strict run with Vault sourced):

- `61 passed, 2 warnings in 1.55s` (UT local-docker)
- `12 passed in 14.24s` (ST local-docker)
- `12 passed in 6.47s` (IT local-docker)
- `7 passed in 7.17s` (AT local-docker)

Backend tier counts:

- UT: pass 61, fail 0, skip 0
- ST: pass 12, fail 0, skip 0
- IT: pass 12, fail 0, skip 0
- AT: pass 7, fail 0, skip 0

Exact UI strict summary lines:

- `npm run lint -- --filter=@cloud-dog/app-index-retriever` -> `Tasks: 8 successful, 8 total` (pass; fail 0)
- `npm run typecheck -- --filter=@cloud-dog/app-index-retriever` -> `Tasks: 8 successful, 8 total` (pass; fail 0)
- `npm run e2e -- --filter=@cloud-dog/app-index-retriever` -> `12 passed (25.8s)` (pass 12, fail 0, skip 0)
- `npm run a11y -- --filter=@cloud-dog/app-index-retriever` -> `2 passed (13.4s)` (pass 2, fail 0, skip 0)

Capability gate evidence:

- Socket connectivity prechecks:
  - `127.0.0.1:8686 CONNECT_OK`
  - `127.0.0.1:8687 CONNECT_OK`

Evidence artefacts:

- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-lint.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-typecheck.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-e2e.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/.turbo/turbo-a11y.log`
- `cloud-dog-ai-ui-monorepo/apps/index-retriever/test-results/.last-run.json`

### Database Abstraction Tests (cloud_dog_db)

| Test ID | Tier | Description | Traces To |
|---------|------|-------------|-----------|
| UT-DB-01 | UT | cloud_dog_db engine factory creates valid SQLite engine from config | R-DB-01, R-DB-02 |
| UT-DB-02 | UT | Session manager provides working sessions | R-DB-01, R-DB-03 |
| ST-DB-01 | ST | Schema migration init→current on fresh SQLite | R-DB-04 |
| ST-DB-02 | ST | CRUD operations via repository abstraction | R-DB-01 |
| IT-DB-01 | IT | Full app startup with cloud_dog_db engine | R-DB-02 |
| AT-DB-01 | AT | End-to-end flow uses cloud_dog_db path | R-DB-01 |
