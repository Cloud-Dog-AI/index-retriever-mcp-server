# index-retriever-mcp-server — Test Plan

**Version:** 1.1  
**Date:** 2026-02-24  
**Standard:** PS-95  
**Current executed cases:** 61 UT + 12 ST + 12 IT + 6 AT + 5 QT + 3 CT = 99

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

## Unit Tests (UT) — 30 tests

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

## Integration Tests (IT) — 12 tests

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

---

## Application Tests (AT) — 5 tests

End-to-end user workflows.

| ID | Test | Description |
|----|------|-------------|
| AT1.1 | FullWorkflow_UploadSearchRetrieve | Upload file → wait for job → search → retrieve chunks → verify content |
| AT1.2 | FullWorkflow_DeduplicateSkip | Duplicate skip, replace-on-change, and stale-triggered reindex behaviours |
| AT1.3 | FullWorkflow_ProfileCollectionLifecycle | Admin creates profile → creates collection → ingests → searches → deletes collection |
| AT1.4 | FullWorkflow_RetentionEnforcement | Ingest documents → run retention with age policy → verify old docs removed |
| AT1.5 | FullWorkflow_MultiBackendSwitch | Create two profiles (Chroma, Qdrant) → ingest to both → search both → same contract |

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
