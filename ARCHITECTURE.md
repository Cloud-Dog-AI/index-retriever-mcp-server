# index-retriever-mcp-server Architecture

**Version:** 1.0  
**Date:** 2026-02-17  
**Standards:** PS-00, PS-10, PS-20, PS-40, PS-50, PS-60, PS-70, PS-75, PS-80, PS-90, PS-95  
**Platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_llm`, `cloud_dog_vdb`

---

## 1. Overview

The service wraps LlamaIndex (and optionally LangChain) to deliver a consistent operational surface for:
- ingestion (upload/text/reference/stream),
- conversion + parsing + chunking,
- embedding via external providers,
- indexing into pluggable vector backends,
- searching and retrieval with metadata management,
- job queueing and operational control,
- audit logging and RBAC,
- Admin WebUI.

**API-first:** HTTP API is canonical; MCP tools and WebUI call into the same handlers.

### 1.1 Route-prefix contract (W14A-04)
- API canonical base path: `/app/v1`
- MCP canonical base path: `/mcp` (catalogue `GET /mcp/tools`)
- Web canonical base path: `/`
- A2A canonical base path: `/a2a`
- Runtime preserves `/api/v1` as compatibility alias for API tool routes while canonical tests/docs target `/app/v1`.
- A2A namespace endpoints:
  - `GET /a2a` (auth-gated namespace probe),
  - `GET /a2a/health` (auth-gated health probe).
- A2A auth uses the same API-key authority as API tool routes (`X-API-Key` and `Authorization: Bearer <api-key>` are validated by one shared key validator).

---

## 2. Recommended Repository Layout

```
repo/
  REQUIREMENTS.txt
  REQUIREMENTS.md
  ARCHITECTURE.md
  defaults.yaml
  config.yaml
  .env
  src/
    index_tools/                    # reusable library (NO server concerns)
      __init__.py
      config/
        __init__.py
        loader.py                   # cloud_dog_config integration: precedence + Vault
        models.py                   # Pydantic config models (profiles, backends, policies)
      security/
        __init__.py
        scope.py                    # connector scopes (fs roots, allowed URIs)
        rbac.py                     # cloud_dog_idam RBAC integration
      audit/
        __init__.py
        logger.py                   # cloud_dog_logging audit writer (JSONL)
        events.py                   # typed audit event definitions
      queue/
        __init__.py
        models.py                   # cloud_dog_jobs job models
        engine.py                   # cloud_dog_jobs worker integration
        redis_bridge.py             # optional Redis/Valkey multiplier (via cloud_dog_jobs)
      connectors/
        __init__.py
        filesystem.py
        s3.py
        webdav.py
        ftp.py
        gdrive.py
        http.py                     # optional
      convert/
        __init__.py
        registry.py                 # converter backend registry
        pandoc.py
        pdf.py
        office.py
        deepdoc.py                  # external (optional)
        mineru.py                   # external (optional)
      pipeline/
        __init__.py
        ingest.py                   # orchestration: fetch -> convert -> chunk -> embed -> upsert
        chunking.py
        metadata.py
        dedupe.py
      embeddings/
        __init__.py
        registry.py                 # cloud_dog_llm embedding provider registry
        adapters.py                 # cloud_dog_llm adapter wrappers
      vdb/
        __init__.py
        registry.py                 # cloud_dog_vdb backend registry
        adapters.py                 # cloud_dog_vdb adapter wrappers
      search/
        __init__.py
        query.py                    # filters + hybrid options + rerank hooks
        retrieve.py
      tools/
        __init__.py
        registry.py                 # MCP tool defs + schemas
        definitions.py              # Pydantic IO models per tool
    index_retriever_server/         # transport + auth + routing
      __init__.py
      api_server.py                 # cloud_dog_api_kit FastAPI factory
      mcp_server.py                 # MCP transport (stdio/HTTP)
      streaming.py                  # SSE/WS ingestion + job updates
      auth/
        __init__.py
        middleware.py               # cloud_dog_idam auth middleware
      admin/
        __init__.py
        controllers.py              # profile/collection/user/job admin endpoints
      webui/                        # admin UI assets (future: @cloud-dog/* packages)
      main.py                       # entrypoint
  tests/
    unit/                           # UT tests (mocks allowed)
    system/                         # ST tests (real DB/VDB/services)
    integration/                    # IT tests (cross-component)
    application/                    # AT tests (end-to-end workflows)
    security/                       # QT tests (security/quality)
    contract/                       # backend contract tests (chroma/qdrant/etc)
    conftest.py                     # shared fixtures
  scripts/
    validate-vault.sh               # Vault connectivity check
  private/                          # git-ignored: env files, secrets
  data/                             # git-ignored: uploads, audit, cache
```

**Separation rule**
- `index_tools/` is reusable and contains no server transport code.
- `index_retriever_server/` is a thin wrapper for auth/transport/routing.

---

## 3. Key Components

### 3.1 ConfigLoader (via `cloud_dog_config`)
- Uses `cloud_dog_config` to load and merge config with precedence.
- Precedence: `os.environ → .env → config.yaml → defaults.yaml → Vault`.
- Performs interpolation and schema validation.
- Supports runtime profile persistence (DB) and hot reload.

### 3.2 Queue Engine (via `cloud_dog_jobs`)
- Uses `cloud_dog_jobs` for DB-backed job table(s) with:
  - concurrency caps (global + per profile),
  - retries/backoff,
  - timeouts,
  - ordering keys (e.g. collection, thread_id),
  - idempotency keys.
- Optional Redis/Valkey bridge to scale workers.

### 3.3 Connectors
Uniform fetch interface:
- `resolve(uri) -> FetchPlan`
- `fetch(plan) -> bytes/stream + source metadata`

Scopes and credentials enforced here.

### 3.4 Conversion & Parsing
Runtime parser/OCR/table internals are delegated to `cloud_dog_vdb` pipeline surfaces.
- Index-retriever exposes thin wrappers (`parsers_list`, `parser_test`, `ingest_preview`, `extract_only`, `ocr_run`, `table_extract`).
- Parser chain selection, OCR heuristics, and table extraction internals are not re-implemented locally.
- Outputs include text/markdown and metadata with `source_uri`, `filename`, and `mime_type`.

### 3.5 Pipeline Orchestrator
`fetch -> convert -> parse -> chunk -> embed -> upsert -> commit metadata`
- Applies dedupe before expensive steps when possible.
- Enriches metadata consistently.
- Emits progress events for streaming and job tracking.

### 3.6 Embeddings Providers (via `cloud_dog_llm`)
Uses `cloud_dog_llm` embedding provider adapters.
- OpenAI-compatible and Ollama-compatible APIs via `cloud_dog_llm`.
- Batch sizing, retries, rate limits (managed by `cloud_dog_llm`).
- Optional local HF embeddings.
- Embedding models configured via Vault (`dev.models` section).

### 3.7 Vector DB Adapters (via `cloud_dog_vdb`)
Uses `cloud_dog_vdb` backend adapters. Each backend implements a common contract:
- collections: create/list/delete
- upsert: vectors + metadata
- query: top_k + filters
- delete: by IDs and by filters
- health + optional maintenance ops

### 3.7A Capability planning and diagnostics (VDB 0.4.1)
- Search calls use backend capability descriptors to derive execution plans and guard unsupported operations (for example, metadata filtering when disabled).
- Backend/provider failures in parser/ingestion surfaces are propagated as explicit diagnostic envelopes with secret redaction.
- Infinity backend is wired as a conditional provider path through the same `cloud_dog_vdb` contracts, enabled only when env configuration is present.

### 3.8 Search/Retrieve Layer
- Normalises queries and filter semantics.
- Supports backend-specific enhancements (hybrid, sparse, rerank hooks) via pluggable extensions.

### 3.9 Auth/RBAC (via `cloud_dog_idam`)
- API keys/JWT mandatory — `cloud_dog_idam` middleware.
- RBAC checks per profile/collection/tool — `cloud_dog_idam` RBAC engine.
- Admin-only endpoints guarded.

### 3.10 Audit Logger (via `cloud_dog_logging`)
Append-only JSONL via `cloud_dog_logging` audit logger.
- Redacts secrets (via `cloud_dog_logging` redaction filters).
- Correlates to job IDs and request IDs.

---

## 4. Data Model (conceptual)

- **profiles**
  - id, name, config_json, enabled, created_at, updated_at
- **collections**
  - id, profile_id, name, backend_collection_id, options_json
- **jobs**
  - id, profile_id, collection, type, status, created_at, started_at, finished_at
  - ordering_key, idempotency_key, retries, error, progress_json
- **documents**
  - doc_id, profile_id, collection, source_uri, content_hash, size, modified_at, metadata_json
- **chunks**
  - chunk_id, doc_id, index_id, text_ref, metadata_json

(Actual storage for vectors is in the chosen backend; this DB tracks control-plane metadata.)

---

## 5. Typical Flows

### 5.1 Ingest upload
1. Auth + RBAC
2. Create job row + enqueue
3. Store uploaded bytes (temp/object store) with reference
4. Worker runs pipeline:
   - convert/parse/chunk
   - dedupe check
   - embed
   - upsert into vdb
   - write doc/chunk metadata
5. Audit success/failure
6. Client polls or streams job results

### 5.2 Search
1. Auth + RBAC
2. Build query + filters
3. Vector backend query
4. Retrieve chunk payloads / metadata
5. Return stable IDs + scores + metadata

### 5.3 Streaming ingestion
1. Client opens SSE/WS channel
2. Sends events (`thread_id`, content, metadata)
3. Server buffers/batches per ordering key
4. Emits progress and ack events
5. Jobs created implicitly or tracked as “stream sessions”

### 5.4 Preview and delegated parser tool flow
1. API/MCP call enters index-retriever tool wrapper.
2. Wrapper validates auth/RBAC and maps request shape.
3. Wrapper delegates preview/test/extract/OCR/table operation to `cloud_dog_vdb` parser pipeline APIs.
4. Response returns normalized metadata and diagnostics through PS-20-compatible envelopes.

---

## 6. Deployment

- Run as single service with:
  - HTTP API + admin UI
  - MCP transport
  - worker processes (same image; separate command)
- Storage:
  - Postgres for profiles/jobs/audit references
  - VDB (chroma/qdrant/...)
  - optional object store for uploaded binaries (S3/local)

---

## 7. Explicit exclusions
- LLM chat completion features (embedding only)
- End-user search UI (admin UI only)
