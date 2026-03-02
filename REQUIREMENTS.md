# Requirements — index-retriever-mcp-server

**Version:** 1.1  
**Date:** 2026-02-28  
**Standards:** PS-00, PS-10, PS-20, PS-40, PS-50, PS-60, PS-70, PS-75, PS-80, PS-90, PS-95  
**Platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_llm`, `cloud_dog_vdb`

---

## 1. Purpose

`index-retriever-mcp-server` is an **API-first** service that provides the full range of **vector database indexing, searching, and retrieval** capabilities for agentic flows, exposed via:
- MCP-compatible **A2A tools** (language-neutral),
- an **HTTP API** (canonical interface; WebUI uses it),
- an **Admin WebUI** for operations (profiles/collections/users/jobs/logs/tests).

It is a **wrapper around LlamaIndex** (and optionally LangChain), providing a consistent operational envelope:
- ingestion and conversion of common document types (Pandoc pipeline, optional DeepDoc/MinerU external),
- embedding via **external embedding providers** (OpenAI-compatible, Ollama-compatible, and other providers),
- pluggable vector backends (Chroma local/remote, Qdrant, OpenSearch, Weaviate, PGVector),
- multi-profile multi-collection management,
- deduplication and metadata enrichment,
- job/queue management (DB-backed with optional Redis/Valkey multiplier),
- audit logging, RBAC, groups, API keys, and enterprise auth options.

**No hard-coded values:** configuration precedence is `os.environ → .env → config.yaml → defaults.yaml`.

---

## 2. Core Concepts & Definitions

- **Profile**: A named configuration bundle (`default`, `profile1`, …) that defines:
  - vector backend + connection,
  - default collection/index,
  - ingestion sources and allowed types,
  - embedding provider and model,
  - policies (dedupe, retention, RBAC, rate limits).
- **Collection**: A logical namespace within a vector backend (e.g., Chroma collection, Qdrant collection).
- **Document**: An ingested item (file, text, URL reference) with content, metadata, and derived embeddings.
- **Chunk**: A segment produced from a document during parsing/splitting; the unit typically embedded and indexed.
- **Embedding provider**: External service used to compute embeddings (OpenAI-compatible API, Ollama-compatible API, local HF, etc.).
- **Job**: A queued unit of work (ingest, reindex, delete, compact, migrate, test search, etc.).
- **Connector**: A source fetcher for `filesystem`, `s3`, `webdav`, `ftp`, `google drive`, and direct upload.
- **Audit log**: Append-only record of user/system actions (no secrets).

---

## 3. Stakeholders & Actors

- **Agent/Client**: Uses tools to add/index/retrieve knowledge as part of flows.
- **Admin**: Manages profiles, collections, users/groups, credentials, jobs, audit/logs.
- **Operator**: Deploys the service and monitors health.

Primary goals:
- Reliable indexing and retrieval for agentic workflows.
- Consistent API/Tool contracts across vector backends and embedding providers.
- Strong auditability and controlled access (RBAC).
- Operational safety: dedupe, retention, job queues, deterministic behaviour.

---

## 4. High-level Use Cases

### UC-01: Upload file, index into profile collection, then query
1. `profile_select(profile="default")`
2. `ingest_upload(profile="default", collection="kb", file=..., dedupe="hash") -> job_id`
3. `job_wait(job_id)` (or stream status)
4. `search(profile="default", collection="kb", query="...", top_k=10) -> results`

### UC-02: Index remote reference (S3/WebDAV/Drive) by URI
1. `ingest_reference(profile="p1", uri="s3://bucket/key", options={...}) -> job_id`
2. System fetches, converts, chunks, embeds, indexes.
3. `job_get(job_id)` returns success + stats (chunks, tokens, time).

### UC-03: Stream chat messages and index in near-real-time
1. Client opens stream endpoint (SSE/WS).
2. Client sends message events with metadata (`thread_id`, `user_id`, tags).
3. Server streams acknowledgements; chunk+embed+index pipeline runs asynchronously.
4. Retrieval can reference `thread_id` to fetch stateful knowledge.

### UC-04: Duplicate detection on re-upload
1. `ingest_upload(..., dedupe="hash+size+mtime")`
2. Server computes fingerprints (sha256/xxhash, size, mtime) and checks index metadata.
3. Policy decides:
   - skip duplicates,
   - replace existing,
   - version as new document with link to prior.

### UC-05: Admin creates a new profile and collection at runtime
1. `admin_profile_create(...)` with vdb + embedding settings
2. `admin_collection_create(profile="p2", collection="finance")`
3. Admin tests with `admin_test_search(...)`
4. Profile becomes available without restart (config is persisted).

### UC-06: Retention/cleanup job
1. Admin schedules `retention_run(profile="p1", rule="older_than:90d")`
2. Job removes old data and updates metadata indexes.
3. Audit log includes removed document IDs and reason.

---

## 5. Functional Requirements (FR)

### FR-01 Interfaces: MCP A2A + HTTP API + Admin WebUI (PS-00 P1, PS-20)
- The system SHALL expose an MCP-compatible A2A tool interface.
- The system SHALL expose an HTTP API (via `cloud_dog_api_kit` FastAPI factory) as the canonical interface.
- HTTP API SHALL include correlation IDs, structured error responses, and health endpoints per PS-20.
- The Admin WebUI SHALL call the HTTP API only (PS-00 P1).
- All operations SHALL be available via API (no UI-only behaviour).

### FR-01A Canonical route-prefix contract (W14A-04)
- Canonical API base path SHALL be `/app/v1`.
- Canonical MCP base path SHALL be `/mcp` and catalogue path SHALL be `GET /mcp/tools`.
- Canonical Web base path SHALL be `/`.
- Canonical A2A base path SHALL be `/a2a`.
- Test/runtime env contracts SHALL expose:
  - `TEST_API_BASE_PATH`
  - `TEST_MCP_BASE_PATH`
  - `TEST_WEB_BASE_PATH`
  - `TEST_A2A_BASE_PATH`
- Legacy API path `/api/v1` MAY remain as temporary compatibility alias, but tests and docs SHALL use canonical `/app/v1`.

### FR-01B A2A auth contract parity (W14B-03)
- API runtime SHALL expose `/a2a` and `/a2a/health`.
- `/a2a/health` SHALL return `401` when no authentication is provided.
- `Authorization: Bearer <api-key>` and `X-API-Key: <api-key>` SHALL reuse the same API-key validator and authority.
- For strict local runtime tests, `TEST_A2A_API_KEY=12345678` SHALL be accepted at `/a2a/health` and return `200`.

### FR-02 Configuration precedence and no hard-coded values (PS-80, PS-00 P2)
- SHALL use `cloud_dog_config` for all configuration loading.
- Precedence: `os.environ → .env → config.yaml → defaults.yaml → Vault`.
- SHALL support Vault integration for shared secrets (database, embedding API keys, VDB credentials).
- The system SHALL support `${VAR}` interpolation.
- After startup, all code MUST read from a single GlobalConfig object only.
- The system SHALL NOT hard-code:
  - secrets, endpoints, model names, collection names, filesystem roots, or retention policies.

### FR-03 Multi-profile support (runtime CRUD)
- The system SHALL support multiple profiles.
- The system SHALL allow profiles to be created/updated/deleted at runtime via admin tools/API.
- Each profile SHALL define:
  - vector backend type and connection,
  - collection/index defaults and options,
  - embedding provider config and model,
  - ingestion connector options and allowed sources,
  - dedupe policy,
  - metadata enrichment rules,
  - RBAC bindings and limits.

### FR-04 Authentication (AuthN) (PS-70)
- SHALL use `cloud_dog_idam` for all authentication.
- The system SHALL require authentication for all tool/API calls (except health endpoints).
- The system SHALL support API keys and JWT bearer tokens via `cloud_dog_idam` middleware.
- The system SHALL support enterprise providers (LDAP, Keycloak OIDC, SAML) via `cloud_dog_idam` pluggable providers.
- The system SHALL NOT log credentials or raw tokens.

### FR-05 Authorisation (RBAC) (PS-70)
- SHALL use `cloud_dog_idam` RBAC engine for all authorisation.
- The system SHALL implement RBAC:
  - per profile,
  - per collection,
  - per tool category (ingest/search/admin/jobs).
- Roles SHALL include: `reader`, `writer`, `maintainer`, `admin` (via `cloud_dog_idam`).
- Admin tools SHALL be restricted to admin role.

### FR-06 Audit logging (append-only) (PS-40)
- SHALL use `cloud_dog_logging` for all structured operational logs and audit trail.
- The system SHALL record audit events (JSONL format via `cloud_dog_logging` audit logger) for:
  - ingestion, update, delete, retention,
  - searches and retrievals (optionally sampling),
  - admin config changes,
  - credential changes,
  - job queue operations.
- Audit entries SHALL include:
  - timestamp UTC,
  - actor identity,
  - profile + collection,
  - operation + redacted params,
  - status + errors/warnings,
  - counts (chunks, docs) and IDs where appropriate.

### FR-07 Job / queue management (PS-75)
- SHALL use `cloud_dog_jobs` for all job queue management.
- The system SHALL implement DB-backed job queue management (via `cloud_dog_jobs`) supporting:
  - concurrency limits,
  - retries with backoff,
  - timeouts,
  - ordering guarantees per profile/collection (configurable),
  - idempotency keys for ingest requests.
- The system SHOULD support Redis/Valkey as an optional throughput multiplier.
- Job tools SHALL include:
  - `job_list`, `job_get`, `job_cancel`, `job_retry`, `job_wait` (blocking/streaming),
  - `queue_status` and worker health.

### FR-08 Ingestion inputs (uploads + text + references)
The system SHALL support ingestion of:
- uploaded files (multipart upload),
- raw text payloads,
- remote references:
  - filesystem paths (within scope),
  - `s3://…`,
  - `webdav(s)://…`,
  - `ftp(s)://…`,
  - Google Drive references (file IDs, shared links),
  - optionally `http(s)://…` if enabled.

### FR-09 Conversion and parsing
- The system SHALL convert common document types into text/markdown for indexing:
  - Office documents (docx/xlsx/pptx),
  - PDF,
  - HTML/XML/Markdown/Text.
- The system SHOULD support Pandoc conversion when available.
- The system SHOULD support optional external enrichers/parsers:
  - DeepDoc,
  - MinerU,
  enabled per profile.
- Conversion SHALL be pluggable (backend registry).
- Timeouts and max input size SHALL be configurable.

### FR-10 Chunking and metadata enrichment
- The system SHALL support configurable chunking strategies per profile:
  - fixed token/char sizes,
  - semantic split (where supported by LlamaIndex),
  - per-filetype splitters.
- The system SHALL enrich metadata at ingest time, including at minimum:
  - source URI/path,
  - filename,
  - size,
  - timestamps (ingested_at, modified_at),
  - content hash/fingerprint,
  - profile, collection,
  - optional tags, tenant, user/thread IDs.
- Metadata schema MUST support management operations (deletion, filtering, retention).

### FR-11 Deduplication
- The system SHALL detect duplicates using configurable strategies:
  - size + mtime,
  - sha256 (or xxhash) fingerprint,
  - combined strategy.
- Dedupe policy options:
  - `skip`,
  - `replace`,
  - `version` (store as new doc with link to prior).
- Dedupe decision MUST be recorded in audit log and job result.

### FR-12 Embedding providers (PS-50)
- SHALL use `cloud_dog_llm` embedding provider adapters for all embedding operations.
- The system SHALL support embedding via external services (via `cloud_dog_llm`):
  - OpenAI-compatible endpoints (including OpenAI, local gateways),
  - Ollama-compatible endpoints,
  - optional local HF embedding models.
- Provider settings per profile:
  - base URL,
  - auth method,
  - model name,
  - batching,
  - rate limits,
  - timeouts and retries.
- The system SHALL support embedding models such as BGE and Nomic via configured providers.
- The system SHALL support provider failover per profile (optional).

### FR-13 Vector backends (pluggable) (PS-60)
- SHALL use `cloud_dog_vdb` for all vector backend operations.
- The system SHALL support (via `cloud_dog_vdb` adapters):
  - Chroma (local & remote),
  - Qdrant,
  - OpenSearch vector,
  - Weaviate,
  - PGVector.
- Backend adapters (provided by `cloud_dog_vdb`) MUST expose a common contract:
  - create/list/delete collection,
  - upsert vectors + metadata,
  - query (top-k + filters),
  - delete by document/chunk IDs and/or metadata filters,
  - maintenance operations where supported (compact, optimize).
- Backend-specific options MUST be configurable per profile.

### FR-13A VDB 0.4.1 adoption requirements (W13B)
- Runtime dependency floor SHALL be `cloud_dog_vdb>=0.4.1` and local Docker build wiring SHALL install the `0.4.1` wheel from `vendor/wheels`.
- Ingest and retrieval metadata SHALL preserve and return `source_uri`, `filename`, and `mime_type` to support deterministic identification, dedupe/reindex decisions, and delete targeting.
- Search execution SHALL be capability-aware per backend profile:
  - capability descriptors SHALL drive plan selection,
  - unsupported filter paths SHALL fail closed with explicit validation errors.
- Provider parse/ingest failures surfaced to API/MCP callers SHALL use explicit diagnostic envelopes with redacted secrets.
- Infinity backend support SHALL be conditional on runtime env availability and SHALL use the same contract path as other adapters.
- Parser/OCR/table internals SHALL remain delegated to `cloud_dog_vdb`; index-retriever SHALL keep control-plane/orchestration scope only.

### FR-14 Search and retrieval
- The system SHALL support:
  - vector similarity search,
  - metadata filtering (where backend supports),
  - hybrid search options (backend-dependent; optional),
  - retrieving source content and/or chunk text,
  - configurable `top_k`, score thresholds, reranking hooks (optional).
- Retrieval MUST return stable identifiers for documents and chunks.
- The `source` value provided at ingest time (`ingest_text`, `ingest_upload`, `ingest_reference`) MUST be preserved and returned in search-result metadata to support traceability and deterministic removal/reindex decisions.

### FR-15 Stateful / streaming ingestion
- The system SHALL support streaming ingestion modes:
  - SSE and/or WebSocket
  - where clients can stream events (e.g., chat messages) and index in near-real-time.
- Ordering guarantees and batching MUST be configurable.

### FR-16 Management operations
Admin/maintainer tools SHALL include:
- profile CRUD (runtime),
- collection CRUD (per profile),
- reindex / rebuild metadata,
- delete / purge by criteria,
- retention cleanup jobs,
- diagnostics (backend connectivity, embedding provider tests),
- test search and retrieval tools.

### FR-17 WebUI/API parity and controlled operations
- The Admin WebUI SHALL be a strict API client (no direct DB/VDB/backend access).
- Every admin operation exposed in MCP/API SHALL be reachable in WebUI with equivalent validation and error semantics.
- WebUI SHALL provide controlled CRUD workflows for:
  - profile management,
  - collection management,
  - connector/ingestion source management,
  - retention/reindex job management.
- WebUI SHALL provide observability views for audit logs, structured logs, job status, and backend health.
- Destructive actions (delete/purge/reindex) SHALL require explicit confirmation and display scope impact before submission.
- WebUI SHALL propagate correlation IDs and machine-readable error codes from API responses.

---

## 6. Non-Functional Requirements (NFR)

- **Security**: secrets never logged; RBAC enforced; connector access constrained; encrypted-at-rest creds if stored.
- **Reliability**: idempotent ingestion; retries with backoff; deterministic job results; recoverable failures.
- **Performance**: configurable caps (file size, chunks, job concurrency); streaming supported; backpressure behaviour defined.
- **Observability**: structured operational logs separate from audit logs; correlation IDs; job metrics.
- **Portability**: POSIX-friendly; external tools optional and discovered at runtime.
- **Extensibility**: plugin adapters for backends, embedding providers, converters, and connectors.
- **WebUI usability/accessibility**: keyboard navigation, WCAG 2.2 AA minimum, and responsive layout for standard desktop/laptop operator viewports.

---

## 7. Tool Catalogue (minimum)

### 7.1 Profile & collection management
- `profiles_list`
- `profile_get`
- `admin_profile_create/update/delete`
- `collections_list`
- `collection_get`
- `admin_collection_create/delete`

### 7.2 Ingestion
- `ingest_upload`
- `ingest_text`
- `ingest_reference`
- `ingest_stream_open` / `ingest_stream_event` / `ingest_stream_close`

### 7.3 Search & retrieval
- `search`
- `retrieve` (by doc/chunk IDs)
- `search_explain` (optional debug)

### 7.4 Jobs / queue
- `job_list`
- `job_get`
- `job_wait` (blocking)
- `job_stream` (SSE/WS)
- `job_cancel`
- `job_retry`
- `queue_status`

### 7.5 Maintenance
- `delete_by_id`
- `delete_by_filter`
- `retention_run`
- `reindex_run`
- `backend_health_check`
- `embedding_health_check`

### 7.6 Delegated parse/preview wrappers (via `cloud_dog_vdb`)
- `parsers_list`
- `parser_test`
- `ingest_preview`
- `extract_only`
- `ocr_run`
- `table_extract`

---

## 8. Acceptance Criteria (examples)

1. A non-admin cannot create or modify profiles.
2. An ingest job can be retried safely without duplicating data when idempotency key is provided.
3. Duplicate upload is handled according to profile policy and recorded.
4. Search returns top_k results with chunk IDs and metadata filters applied.
5. Chroma, Qdrant, and PGVector backends each pass the same contract tests.
6. Streaming ingestion indexes events in order per configured ordering key (e.g., thread_id).
7. Audit log contains profile/collection/job_id and status for all mutating operations.
8. WebUI can complete profile and collection CRUD with API-only calls and matching audit records.
9. WebUI presents backend/embedding/job failures using API machine error codes and correlation IDs.

---

## 9. Out of Scope (explicit)

- End-user document browsing UI (Admin UI only)
- LLM chat completion features (embedding only; retrieval returns data)
- Full data lake governance (beyond profiles, RBAC, retention, audit)
