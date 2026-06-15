---
template-id: T-REQ
template-version: 1.1
applies-to: docs/REQUIREMENTS.md
project: index-retriever-mcp-server
doc-last-updated: 2026-06-12T16:37:04Z
doc-git-commit: 167f371208d2dbe673d692b181cfb25f78d51cb9
doc-git-branch: w28a-749-idam
doc-age-policy: indefinite
doc-conformance-stamp: 2026-06-12T16:37:04Z
req-trace-version: 1.0
req-id-prefixes-used: [SV, BO, BR, FR, UC, CS, NF, R, F]
surface-coverage: [api, mcp, a2a, webui]
---

# Requirements — index-retriever-mcp-server

## Provenance
- Canonical requirements for index-retriever-mcp-server. Reconciled to runtime by W28A-749 (IDAM Thread-b).
- Source basis: `defaults.yaml`, the API/Web/MCP/A2A servers, and the runtime tool registry (92 tools — `src/index_tools/tools/registry.py`, enforced by `UT1_40`).

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
- Canonical API base path SHALL be `/api/v1`.
- Canonical MCP base path SHALL be `/mcp` and catalogue path SHALL be `GET /mcp/tools`.
- Canonical Web base path SHALL be `/`.
- Canonical A2A base path SHALL be `/a2a`.
- Test/runtime env contracts SHALL expose:
  - `TEST_API_BASE_PATH`
  - `TEST_MCP_BASE_PATH`
  - `TEST_WEB_BASE_PATH`
  - `TEST_A2A_BASE_PATH`
- A legacy API alias MAY remain temporarily for backwards compatibility, but tests and docs SHALL use canonical `/api/v1`.

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

### FR-09A OCR provider support and selection
- The system SHALL expose OCR planning and OCR-capable parse flows through delegated `cloud_dog_vdb` ingestion components.
- Supported OCR provider IDs in the effective runtime surface SHALL be:
  - `local`: local command OCR (`tesseract` by default) with configurable `command` and `timeout_seconds`.
  - `external_service`: remote OCR HTTP service with configurable `base_url`, optional `api_key`, and remote `/health` + `/ocr` contract.
  - `llm_ocr`: OpenAI-compatible multimodal OCR with configurable `base_url`, `api_key`, `model`, and `timeout_seconds`.
- OCR selection SHALL support `disabled`, `auto`, and `force` modes through the OCR planner surface.
- OCR planning SHALL accept and preserve `provider_id`, `min_chars`, and `min_scanned_ratio` controls.
- OCR-capable preview/extract flows SHALL surface:
  - selected `ocr_mode`,
  - whether OCR was applied,
  - the provider reason/decision captured in delegated metadata.
- The current runtime SHALL fail closed with explicit diagnostics when an OCR provider is unavailable or misconfigured; automatic cross-provider failover is NOT implemented.
- Quality expectations SHALL be documented as provider-dependent:
  - `local` returns plain-text OCR from the configured local command,
  - `external_service` follows the quality of the remote OCR service,
  - `llm_ocr` depends on the configured multimodal model and prompt contract.

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

### FR-10A Chunking strategy matrix
- The effective implementation SHALL document and preserve the following chunking strategies:
  - `token_overlap`: project `token_chunks(text, chunk_size, chunk_overlap)` token-window splitting with overlap; use when token continuity between adjacent chunks is required.
  - `paragraph`: project `paragraph_chunks(text)` blank-line structural splitting; use when source paragraph boundaries should be preserved exactly.
  - `fixed_size`: delegated `cloud_dog_vdb.ingestion.chunk.fixed.FixedChunker(size)` character-window splitting; use for deterministic fixed-width chunking independent of semantic structure.
  - `semantic`: delegated `cloud_dog_vdb.ingestion.chunk.semantic.SemanticChunker(min_sentence_len)` sentence-aware aggregation around full-stop boundaries; use when chunk boundaries should stay close to sentence semantics.
  - `recursive`: delegated `cloud_dog_vdb.ingestion.chunk.recursive.RecursiveChunker(max_chars)` section/paragraph-preserving splitting with character fallback; use as the default general-purpose strategy for mixed-structure documents.
- Chunking configuration SHALL document these effective parameters:
  - `chunk_size`
  - `chunk_overlap`
  - `chunk_unit`
  - strategy-specific limits such as `size`, `max_chars`, or `min_sentence_len`
- The delegated preview/ingestion pipeline SHALL default to the recursive chunker when no explicit chunker override is supplied.
- Overlap behaviour SHALL apply only to the token-overlap strategy; other strategies SHALL preserve their native boundary logic without synthetic overlap insertion.

### FR-10B Canonical metadata uplift contract (W28A-884 Phase 1)
- The canonical metadata model for `index-retriever-mcp-server` SHALL converge on the `cloud_dog_vdb` metadata contract and SHALL be applied consistently across ingest, retrieval, delete, dedupe, retention, and reindex operations.
- Status tags in this section mean:
  - `EXISTING`: already required elsewhere in this document before W28A-884.
  - `NEW`: introduced normatively by this uplift and not previously required as part of the canonical contract.
- During migration, compatibility aliases MAY be preserved where already emitted today, but the canonical field names below SHALL become the normative contract.

#### FR-10B.1 Identity and lineage
- `doc_id` SHALL be returned on retrieval and search results and SHALL become the canonical document identity. `EXISTING`
- `doc_id` generation SHALL converge on deterministic package-owned computation rather than service-local ad hoc generation. `NEW`
- `record_id` SHALL identify the stored record written to the backend and SHALL be preserved for package-owned ingest/upsert and delete targeting. `NEW`
- `chunk_id` SHALL identify the logical chunk within a document and SHALL remain stable across retrieval and delete/filter operations. `EXISTING`
- `supersedes` SHALL identify the prior `doc_id` or `record_id` replaced by a versioning or dedupe operation. `NEW`
- `is_latest` SHALL indicate whether a record is the current live version for a source lineage. `NEW`

#### FR-10B.2 Source reference
- `source_uri` SHALL remain the canonical source locator for traceability, delete targeting, and deterministic identity inputs. `EXISTING`
- `filename` SHALL remain preserved and returned where derivable from the source reference or uploaded asset. `EXISTING`
- `mime_type` SHALL remain preserved and returned with ingest and retrieval metadata. `EXISTING`
- `size_bytes` SHALL become the canonical byte-size field for source payload size. Existing `size` output MAY remain as a temporary compatibility alias during migration. `NEW`

#### FR-10B.3 Integrity
- `content_hash` SHALL remain preserved as the canonical hash of the indexed content used for dedupe and lineage decisions. `EXISTING`
- `source_hash` SHALL be added as the canonical hash of the original source payload where available so dedupe and reindex decisions can distinguish source changes from chunking or embedding changes. `NEW`

#### FR-10B.4 Time and lifecycle
- `created_at` SHALL become a required UTC RFC3339 lifecycle timestamp for the canonical metadata contract. `NEW`
- `ingested_at` SHALL remain preserved as the ingest-time timestamp surfaced to callers. `EXISTING`
- `lifecycle_state` SHALL become a required canonical lifecycle field for active, superseded, deleted, or archived records. `NEW`
- `ttl_days` SHALL be added as the canonical retention-policy field carried with records when retention rules are material to lifecycle processing. `NEW`

#### FR-10B.5 Attribution
- `app_id` SHALL identify the calling application or integration surface when supplied by the control plane. `NEW`
- `user_id` SHALL be preserved when user-scoped ingest or stream events are supplied. `EXISTING`
- `session_id` SHALL be the canonical session or conversation identifier for stateful ingest and retrieval correlation. `NEW`
- `profile` SHALL remain preserved as the service profile context. `EXISTING`
- `collection` SHALL remain preserved as the collection/index namespace. `EXISTING`

#### FR-10B.6 Embedding reproducibility
- `embedding_model` SHALL be preserved with each indexed record to support deterministic rebuild, parity validation, and backend troubleshooting. `NEW`
- `embedding_dim` SHALL be preserved where known so collection-write and parity checks can verify embedding compatibility. `NEW`
- `chunker` SHALL be preserved as the canonical chunking strategy or chunker version used to produce the record. `NEW`
- `token_count` SHALL be preserved where available for sizing, retention, and reproducibility analysis. `NEW`

#### FR-10B.7 Governance
- `access_tags` SHALL carry portable access-control labels used by metadata filters and policy enforcement. `NEW`
- `pii_present` SHALL carry a canonical boolean or equivalent flag indicating whether PII was detected or asserted for the record. `NEW`

#### FR-10B.8 Additive provenance
- `parser` SHALL carry the selected parser provider and version lineage in canonical form. `NEW`
- `ocr` SHALL carry OCR mode, provider, and decision provenance in canonical form. `NEW`
- `page` SHALL carry page-level provenance where chunk origin is page-scoped. `NEW`
- `section` SHALL carry section or heading provenance where extractors provide it. `NEW`
- `table` SHALL carry table provenance and table-shape references where table extraction contributes to the record. `NEW`
- `chunk_kind` SHALL distinguish narrative, table, OCR, caption, or other chunk classes where the parser pipeline can determine them. `NEW`

#### FR-10B.9 Boundary rule for metadata ownership
- `index-retriever-mcp-server` SHALL own transport-level request shaping, caller attribution, profile/collection resolution, and API/MCP response formatting.
- `cloud_dog_vdb` SHALL own canonical metadata schema definition, validation, deterministic identifier helpers, parser/OCR/table provenance normalization, and backend-portable lifecycle/filter semantics.
- Service-local metadata shaping that duplicates package-owned canonical rules SHALL be treated as transitional only and SHALL be retired as the package uplift lands.

#### FR-10B.10 Metadata-pack compatibility and management filters
- The implementation SHALL preserve compatibility with the archived metadata-pack baseline in `cloud-dog-ai-platform-standards/archive/working-2026-05/evidence-dirs/metadata-pack/`.
- Every ingested record SHALL emit the metadata-pack identity aliases `document_id` and `index_record_id` alongside the active `doc_id` and `record_id` fields until downstream callers have migrated.
- Every ingested record SHALL emit the metadata-pack management fields `dataset_id`, `collection_id`, `title`, `language`, `status`, `authoritative_source`, `updated_at`, `embedding_dimensions`, `embedding_version`, `index_version`, `pipeline_version`, `chunking_strategy`, `normalisation_version`, `index_family`, `visibility`, `access_scope`, and `retention_class`.
- Search, retrieve, delete-by-filter, retention, and lifecycle operations SHALL keep `status` aligned with `lifecycle_state` so records can be filtered by active, superseded, deleted, or archived state.
- Metadata filters SHALL support exact filtering for the metadata-pack mandatory query baseline: `tenant_id`, `dataset_id`, `collection_id`, `document_id`, `chunk_id`, `status`, `language`, `source_type`, `authoritative_source`, `updated_at`, `ingested_at`, `embedding_model`, and `index_version`.
- Local and backend-backed filtering SHALL support comparison operator objects for time/window filters where the API/MCP caller supplies `gt`, `gte`, `lt`, `lte`, `eq`, `ne`, or `in` forms.
- Unit and integration tests SHALL prove metadata-pack field emission, retrieve/search round-trip, lifecycle status alignment, and date/operator filtering.

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

### FR-13B W23A full `cloud_dog_vdb` integration requirements

#### R-VDB (backend breadth and contract parity)
- **R-VDB-01:** The system SHALL support all six `cloud_dog_vdb` adapters: `chroma`, `qdrant`, `opensearch`, `pgvector`, `weaviate`, `infinity`.
- **R-VDB-02:** Each enabled backend SHALL pass the same CRUD/search contract tests (create collection, upsert, top-k search, delete, empty verification).
- **R-VDB-03:** Backend selection SHALL be profile-scoped and switchable without code changes.
- **R-VDB-04:** Health checks SHALL be enforced per backend before live ingest/search operations.
- **R-VDB-05:** Unsupported backend capability paths SHALL fail closed with explicit diagnostics (no silent fallback).
- **R-VDB-06:** Infinity support remains conditional on environment/Vault configuration and SHALL follow the same adapter contract path.

#### R-PARSE (parser breadth, fallback, OCR/table)
- **R-PARSE-01:** The parser provider matrix SHALL cover `deepdoc`, `docling`, `mineru`, `marker_mcp`, `transformers`, `internal`.
- **R-PARSE-02:** Parser selection SHALL be configurable per profile and per request parser chain.
- **R-PARSE-03:** Parser fallback chain SHALL execute deterministically in configured order and surface failure causes.
- **R-PARSE-04:** Parser output SHALL be normalized to the IR contract (`text_blocks`, `table_blocks`, `quality`, provider/version metadata).
- **R-PARSE-05:** Parser provider health probing SHALL be exposed for runtime diagnostics.
- **R-PARSE-06:** OCR-enabled parsing SHALL be testable against real image-heavy corpus samples.
- **R-PARSE-07:** Table extraction SHALL be testable against table-heavy corpus samples with structured outputs.

#### R-CONSIST (cross-backend consistency)
- **R-CONSIST-01:** Ingest/search round-trip for identical payloads SHALL be consistent across backend pairs.
- **R-CONSIST-02:** Metadata parity (`source_uri`, `filename`, `mime_type`, tenant/document markers) SHALL hold across backends.
- **R-CONSIST-03:** Delete-by-id/filter semantics SHALL remove indexed content consistently across enabled backends.
- **R-CONSIST-04:** Collection lifecycle (create/list/delete) SHALL preserve the same observable contract across backends.

#### R-EMBED (multi-provider embedding operations)
- **R-EMBED-01:** Embedding provider routing SHALL support Vault-configured multi-model operation.
- **R-EMBED-02:** Embedding dimension validation SHALL be enforced before backend collection writes.
- **R-EMBED-03:** Embedding model failure paths SHALL fail closed with explicit provider diagnostics (no silent downgrade).
- **R-EMBED-04:** Live application tests SHALL exercise `bge-m3:567m`, `nomic-embed-text`, and `granite-embedding:278m`.

### FR-14 Search and retrieval
- The system SHALL support:
  - vector similarity search,
  - metadata filtering (where backend supports),
  - hybrid search options (backend-dependent; optional),
  - retrieving source content and/or chunk text,
  - configurable `top_k`, score thresholds, reranking hooks (optional).
- Retrieval MUST return stable identifiers for documents and chunks.
- The `source` value provided at ingest time (`ingest_text`, `ingest_upload`, `ingest_reference`) MUST be preserved and returned in search-result metadata to support traceability and deterministic removal/reindex decisions.

### FR-14A Retrieval output contract and effective output modes
- The active search contract SHALL return inline content for each hit:
  - API/service search returns chunk text in the result body (`text` or runtime-equivalent `content` field),
  - stable `doc_id` / `chunk_id` identifiers,
  - similarity `score`,
  - `metadata` containing source traceability.
- The active retrieve-by-ID contract SHALL return stored content inline together with:
  - `doc_id`,
  - `profile`,
  - `collection`,
  - original `source`,
  - full `metadata`.
- Source-link output SHALL currently be represented by preserved `source` / `metadata.source_uri` values rather than a separate selectable output-mode parameter.
- The active service/runtime does NOT currently expose a selectable `output_mode` or base64 file-return parameter on `search` or `retrieve`; parser backends may use base64 transport internally, but the retrieval contract delivered by this service is inline content plus source-URI traceability.

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

### FR-16A Complete MCP tool inventory contract
- The documented MCP catalogue SHALL match the actual registered runtime inventory exactly.
- The current registered tool count SHALL be **92** tools (verified: `src/index_tools/tools/registry.py` runtime build = 92 unique; `UT1_40` asserts `len(tools) == 92`; includes the 21 W28E-603 document-structure tools). Reconciled to runtime by W28A-749.
- Tool documentation SHALL include, for every registered tool:
  - tool name,
  - operator intent/description,
  - primary input parameters,
  - expected output contract.
- Adding or removing a registered tool SHALL require the catalogue in section 7 to be updated in the same change.

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

### FR-P001 Ingest Preview
- The server SHALL provide an `ingest_preview` tool that shows the chunking and embedding
  plan for a document without executing the actual ingest pipeline.

### FR-P002 Search Explain
- The server SHALL provide a `search_explain` tool that returns the scoring breakdown
  and retrieval strategy used for a search query.

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

### 7.7 Complete runtime tool inventory (92 tools)

| Tool | Purpose | Primary inputs | Expected output |
|------|---------|----------------|-----------------|
| `profiles_list` | List available profiles. | none / generic profile context | profile list payload |
| `profile_get` | Get one profile definition. | `profile` | profile payload |
| `admin_profile_create` | Create a profile at runtime. | `profile`, profile config | status/profile payload |
| `admin_profile_update` | Update a runtime profile. | `profile`, profile config | status/profile payload |
| `admin_profile_delete` | Delete a runtime profile. | `profile` | status payload |
| `users_list` | List users. | none / generic profile context | user list payload |
| `user_get` | Get one user. | `user_id` | user payload |
| `admin_user_create` | Create a user. | `user_id`, user fields, role/group bindings | status/user payload |
| `admin_user_update` | Update a user. | `user_id`, mutable user fields | status/user payload |
| `admin_user_delete` | Delete a user. | `user_id` | status payload |
| `groups_list` | List groups. | none / generic profile context | group list payload |
| `group_get` | Get one group. | `group_id` | group payload |
| `admin_group_create` | Create a group. | `group_id`, group fields | status/group payload |
| `admin_group_update` | Update a group. | `group_id`, mutable group fields | status/group payload |
| `admin_group_delete` | Delete a group. | `group_id` | status payload |
| `api_keys_list` | List issued API keys. | none / generic profile context | API-key list payload |
| `admin_api_key_create` | Issue an API key. | subject/user binding, roles, expiry options | created key/status payload |
| `admin_api_key_revoke` | Revoke an API key. | `key_id` | status payload |
| `a2a_config_events` | List configuration-change events. | none / generic profile context | config event list |
| `collections_list` | List collections in a profile. | `profile` | collection list payload |
| `collection_get` | Get one collection. | `profile`, `collection` | collection payload |
| `admin_collection_create` | Create a collection. | `profile`, `collection`, metadata/options | status/collection payload |
| `admin_collection_update` | Update collection metadata/options. | `profile`, `collection`, mutable fields | status/collection payload |
| `admin_collection_delete` | Delete a collection. | `profile`, `collection` | status payload |
| `source_configs_list` | List source/connector configs. | `profile` | source config list |
| `source_config_get` | Get one source config. | `profile`, source-config ID | source config payload |
| `admin_source_config_create` | Create a source config. | `profile`, source config definition | status/source-config payload |
| `admin_source_config_update` | Update a source config. | `profile`, source-config ID, mutable fields | status/source-config payload |
| `admin_source_config_delete` | Delete a source config. | `profile`, source-config ID | status payload |
| `rbac_bindings_list` | List RBAC bindings. | scope/profile context | RBAC binding list |
| `admin_rbac_bind` | Bind a role. | entity type, entity ID, role, scope | status/binding payload |
| `admin_rbac_unbind` | Remove a role binding. | entity type, entity ID, role, scope | status payload |
| `ingest_upload` | Ingest uploaded file content. | `profile`, `collection`, upload payload, source metadata | `job_id`, status |
| `ingest_text` | Ingest raw text. | `profile`, `collection`, `text`, `source` | `job_id`, status |
| `ingest_reference` | Ingest a remote/local reference. | `profile`, `collection`, `uri`/reference options | `job_id`, status |
| `parsers_list` | List delegated parser providers. | optional `parser_services` | parser list with capabilities |
| `parser_test` | Probe one parser provider. | `provider_id`, sample text/source URI, parser services/options | provider health/quality payload |
| `ingest_preview` | Preview parse/chunk/OCR outcome without persistence. | text/source URI, parser chain/options, OCR/table options | preview payload with chunk count and checkpoints |
| `extract_only` | Extract text without persistence. | text/source URI, parser chain/options, OCR/table options | extracted text payload |
| `ocr_run` | Evaluate OCR planner/provider selection. | text size/scanned-ratio inputs, `mode`, `provider_id` | OCR decision payload |
| `table_extract` | Extract/render tables without persistence. | text/source URI, parser chain/options, table policy | table extraction payload |
| `ingest_stream_open` | Open a streaming ingest session. | profile/collection/session context | stream session status |
| `ingest_stream_event` | Append one streaming ingest event. | session ID/event payload | `job_id`, status |
| `ingest_stream_close` | Close a streaming ingest session. | session ID | status payload |
| `search` | Execute vector search. | `profile`, `collection`, `query`, `top_k`, filters | ranked search results |
| `retrieve` | Retrieve a stored record by ID. | `doc_id` | content + metadata payload |
| `search_explain` | Return search plan/scoring breakdown. | `profile`, `collection`, `query`, `top_k`, filters | explain/plan payload |
| `job_list` | List jobs. | scope/profile filters | job list payload |
| `job_get` | Get one job. | `job_id` | job payload |
| `job_wait` | Wait for a job to finish. | `job_id`, wait options | terminal job payload |
| `job_stream` | Stream job progress. | `job_id` | streaming/progress payload |
| `job_cancel` | Cancel a job. | `job_id` | status payload |
| `job_retry` | Retry a job. | `job_id` | status/new-job payload |
| `queue_status` | Inspect queue health and backlog. | none / generic profile context | queue status payload |
| `delete_by_id` | Delete one record. | `profile`, `collection`, `doc_id` | status payload |
| `delete_by_filter` | Delete matching records. | `profile`, `collection`, metadata filters | deleted-count/status payload |
| `retention_run` | Execute retention cleanup. | `profile`, `collection`, retention rule/age | deleted-count/status payload |
| `reindex_run` | Reindex a collection/profile. | `profile`, `collection`, reindex options | status/job payload |
| `backend_health_check` | Check VDB backend health. | optional provider context | backend health payload |
| `embedding_health_check` | Check embedding provider health. | optional provider/model context | embedding health payload |

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

### Database Abstraction (cloud_dog_db adoption)

- R-DB-01: All database access MUST use `cloud_dog_db` engine/session/CRUD abstractions
- R-DB-02: Engine creation MUST use `cloud_dog_db` engine factories
- R-DB-03: Session management MUST use `cloud_dog_db.session.SyncSessionManager`/`AsyncSessionManager`
- R-DB-04: Schema migrations MUST use `cloud_dog_db` migration runner
- R-DB-05: Direct sqlite3/create_engine()/sessionmaker()/raw Session() FORBIDDEN in app code
- R-DB-06: DB health MUST use `cloud_dog_db.health.probe_database()`
- R-DB-07: DB connection config MUST come from cloud_dog_config/Vault-backed env hierarchy
- R-DB-08: Schema versioning MUST be tested across SQLite, MySQL, and PostgreSQL
- R-DB-09: Schema upgrade/downgrade MUST be validated with at least two migrations per dialect
- R-DB-10: CRUD outcomes MUST be consistent across SQLite, MySQL, and PostgreSQL

## Configuration CRUD Requirements (CFG)

Profile concept for this project: index and retrieval profiles defining vector backend, embedding provider, collection defaults, ingestion policy, retention, and RBAC.

| ID | Requirement |
|----|-------------|
| CFG-01 | The system SHALL support creating a new index profile via the API with all profile settings that would otherwise be available via environment variables or env-file configuration. |
| CFG-02 | The system SHALL support reading index profiles via the API, including both list and detail retrieval. |
| CFG-03 | The system SHALL support updating an existing index profile via the API. |
| CFG-04 | The system SHALL support deleting an index profile via the API. |
| CFG-05 | Index profile CRUD operations SHALL be available as MCP tools with equivalent functionality. |
| CFG-06 | Index profile change events SHALL be broadcast via the A2A interface per **PS-72 §A2A-change-events** (canonical envelope `{type, topic, timestamp, payload}`; reference implementation `cloud_dog_api_kit.a2a.events` ≥0.11.0; see platform-standards `docs/standards/PS-72-agent-to-agent.md`). |
| CFG-07 | Index profile CRUD operations SHALL be available in the WebUI with RBAC enforcement. |
| CFG-08 | The system SHALL support creating, reading, updating, and deleting users via the API. |
| CFG-09 | The system SHALL support creating, reading, updating, and deleting groups with role assignments via the API. |
| CFG-10 | The system SHALL support creating, listing, and revoking API keys with per-key capability scoping via the API. |
| CFG-11 | User, group, and API-key management SHALL be available via MCP, A2A, and WebUI with RBAC. |
| CFG-12 | All CRUD operations SHALL be audit logged with user identity, action, timestamp, and outcome. |
| CFG-13 | Only admin users SHALL be able to create, update, and delete index profiles and manage users or groups; read-only access SHALL be available to authorised non-admin users. |


## W28A-883 PS-78 Cross-Platform File Handling Addendum

### Verified current state

- The service already supports ingest upload through the API and MCP: `UploadFile` handling in `api_server.py` and the `ingest_upload` tool in the MCP service layer.
- The WebUI `IngestSearchPage` already uses `FileDropZone` and upload actions for browser-driven ingest.
- Current file handling is ingest-centric. No standard file inventory, delete, or binary download lifecycle was found.

### Required additions to satisfy PS-78

- Extend the ingest-only contract to the full file lifecycle: `/files/upload`, `/files/upload_base64`, `/files`, `/files/{id}`, `DELETE /files/{id}`, and `/files/{id}/download`.
- Add standard MCP file upload/download contracts in addition to `ingest_upload`.
- Add A2A file transfer payloads for document exchange between retrieval agents.
- Add URI-source intake for `http://`, `https://`, `s3://`, `ftp://`, and `file://` under explicit policy instead of limiting defaults to upload/text.
- Add WebUI file inventory and download/delete surfaces for uploaded documents and derived artifacts.

### Required PS-78 test plan

- API: upload, list, download, delete, metadata verification.
- MCP: `ingest_upload`, base64 upload/download, URI-source intake.
- A2A: send a document reference or base64 payload to another retrieval-capable agent.
- WebUI: `FileDropZone` upload, inventory view, download, delete.
- Retrieval flow: upload document, verify searchable ingest, then verify the stored file lifecycle contract independently of retrieval results.

## W28A-906 WebUI Standards Merge Addendum

This addendum merges the 13-section `INDEX-RETRIEVER-E2E-TEST-SPEC.md` UI scope into normative requirements.

Status labels:
- `EXISTING`: already required elsewhere in this document before W28A-906.
- `NEW`: made explicit by W28A-906 because the prior requirements did not state the WebUI contract clearly enough.

### a) Profile Configuration — CRUD, VDB Backend Binding, and RBAC
- `EXISTING`: The WebUI SHALL provide profile CRUD with vector-backend selection/binding and RBAC-governed mutation controls for runtime profiles.

### b) Collection Management — CRUD and Backend-Aware Configuration
- `EXISTING`: The WebUI SHALL provide collection CRUD with backend-aware collection settings, dimensions/metric controls, metadata/options, and RBAC-governed mutation controls.

### c) Source Configuration — CRUD, Connector Types, and Schedule
- `EXISTING`: The WebUI SHALL provide source-config CRUD with connector-type selection, profile/collection targeting, URI/reference fields, schedule fields, and RBAC-governed mutation controls.

### d) Ingest — Text, Upload, Reference, Stream, and Metadata Verification
- `EXISTING`: The WebUI SHALL provide ingest workflows for text, file upload, URI/reference intake, and streaming/session-oriented ingest surfaces backed by the canonical API/tool contracts.
- `NEW`: The WebUI SHALL expose canonical metadata entry and post-ingest metadata inspection for ingest operations, including the standard metadata fields uplifted in W28A-884 to W28A-887.

### e) Search, Retrieve, and Explain — Semantic and Metadata Filtering
- `EXISTING`: The WebUI SHALL provide search and retrieve workflows for indexed content, including result paging, result export, and document/record retrieval.
- `NEW`: The WebUI SHALL provide metadata-filter entry, metadata inspection, and search-explain visibility for search and retrieval workflows.

### f) Retention, Delete, Reindex, and Lifecycle
- `EXISTING`: The WebUI SHALL provide retention, delete-by-id, delete-by-filter, and reindex controls with explicit confirmation for destructive operations.
- `NEW`: The WebUI SHALL expose lifecycle-oriented state and filter surfaces needed to operate retention, delete, and reindex workflows safely.

### g) Parser, OCR, and Table Extraction Preview
- `EXISTING`: The service SHALL expose parser, OCR, ingest-preview, extract-only, and table-extraction capabilities through the API/MCP surface.
- `NEW`: The WebUI SHALL expose parser, OCR, and table-extraction preview workflows with operator-visible extracted content, structured metadata, and provenance details.

### h) Cross-Backend Verification — Same Content, Multiple VDBs
- `NEW`: The WebUI SHALL support operator verification that the same content can be ingested, searched, and compared across the supported vector backends: Qdrant, Chroma, OpenSearch, PGVector, and Weaviate.

### i) Jobs — Async Ingest, Sync, and Retention Monitoring
- `EXISTING`: The WebUI SHALL expose job-listing, job-detail, status, retry, cancel, and export capabilities for ingest, sync, reindex, and retention workflows.

### j) Observability and Audit — Structured Logs and Metrics
- `EXISTING`: The WebUI SHALL expose operational health, queue state, backend/embedding health, structured logs, audit-log inspection, and related operator metrics.

### k) Dashboard — Operational Health and Metrics
- `EXISTING`: The WebUI SHALL provide a dashboard surface for operational health, system metrics, quick actions, and recent operator-visible activity.

### l) Canonical Metadata Round-Trip Verification
- `NEW`: The WebUI SHALL support operator verification of canonical metadata round-trip behavior for ingest, search, retrieve, lifecycle, and delete flows, aligned to the W28A-884 to W28A-887 metadata uplift.

### m) Full Audit Trail Log Verification
- `NEW`: The WebUI SHALL support operator verification that mutating operations across sections a-l produce corresponding audit trail records with actor, target, action, outcome, correlation/trace information, and timestamps.

### Shared WebUI Standards Expectations Across Sections a-m
- `NEW`: CRUD-oriented views SHALL use `DataTable` with `EntityDialog` for add/edit/view interactions unless a stricter platform standard supersedes that pairing.
- `NEW`: Search/filter-oriented views SHALL use `SearchPanel` where free-text or structured filtering is part of the operator workflow.
- `NEW`: Structured metadata/config/result inspection views SHALL use `JsonExplorer` instead of raw JSON blocks where hierarchical inspection is required.
- `NEW`: Code/content/result viewers and editors SHALL use `CodeViewer` and `CodeEditor` where extracted text, prompt/config JSON, diff-like content, or preview payloads require governed editor/viewer behavior.
- `NEW`: API/MCP/A2A documentation surfaces SHALL use `ApiDocsPanel` with tabbed documentation where multiple protocol/reference families are presented together.

## PS-40 / W28A-619 Logging and Audit Requirements

The service MUST use `cloud_dog_logging` as the only application and audit logging implementation. Raw stdlib logging setup, direct `logging.getLogger()` calls, bespoke audit emitters, and print-based operational logging are not compliant except inside the platform logging package itself.

Every auditable event MUST emit a PS-40/NIST AU-3 audit record with: `event_type`, `action`, `timestamp`, `service`, `component`, `service_instance`, `environment`, `source_host`, `source_process`, `source_application`, `source_address` where available, `destination_address` where available, `outcome`, actor identity including user/service/system plus account/process/device identifiers where available, `target`, `process_id`, `affected_files` where relevant, `correlation_id`, `trace_id`, and `request_id`.

Auditable events MUST include authentication and authorisation decisions, user/group/API-key/RBAC changes, profile/collection/source/ingest/search/retrieve/delete/retention/reindex/parser/OCR operations, MCP/A2A/API calls, job lifecycle changes, configuration changes, data access and mutation, denials, failures, and privileged operations. Secrets MUST be redacted before persistence. Tests MUST cover schema fields, event coverage, redaction, append-only audit persistence, retention/integrity, and WebUI observability rendering/filtering.

## 5. Cyber Security & Negative Flows

Mandatory schema per PS-REQ-TEST-TRACE v1.0 §3.4. Every project covers anon-denied, wrong-role-denied, missing-param-error per declared surface. The CS rows below are platform-baseline; project-specific extensions append in §5.1.

| ID | Threat / negative scenario | Surface | Role(s) attempted | Expected | Tests |
|---|---|---|---|---|---|
| `CS-001` | Anon attempts data read | `api`, `mcp`, `a2a`, `webui` | `anon` | `401` | (to be bound in Instruction 4 by operator) |
| `CS-002` | read-only attempts write | `api`, `mcp` | `read-only` | `403` | (to be bound in Instruction 4 by operator) |
| `CS-003` | Missing required param | `api` | `admin` | `422` | (to be bound in Instruction 4 by operator) |
| `CS-004` | Wrong-role privileged op | `mcp` | `read-write` | `403` | (to be bound in Instruction 4 by operator) |


<!-- W28C-1710b design-delta additions (2026-06-14T18:01:23Z); SHA chain in working/W28C-1710b/KNOWLEDGE-PRESERVATION-DELTA.md -->

## PS-REQ-TEST-TRACE schema completion (W28C-1710b)

Per the binding contract (`docs/standards/PS-REQ-TEST-TRACE.md` §2 + §3), every FR-NNN row in this file declares the following schema (default values; operator amends per row in W28C-1711):

```yaml
surface: ['api', 'mcp', 'a2a']  # programme default for index-retriever-mcp-server
priority: must  # default; operator amends per FR
since: 2026-06-14  # carried forward unless older anchor known
last-verified: 2026-06-14
tests: []  # populated by W28C-1711 binding
crud: N/A  # default; operator amends per FR
```

## Baseline CS-NNN rows (PS-REQ-TEST-TRACE §3.4 — added by W28C-1710b)

Every project MUST have CS-NNN rows for `anon-denied`, `wrong-role-denied`, `missing-param-error` per surface. Programme baseline:

| CS-NNN | Scenario | Surface | Expected | Roles |
|---|---|---|---|---|
| `CS-005` | anon-denied | `api` | `401` | `anon` |
| `CS-006` | anon-denied | `mcp` | `401` | `anon` |
| `CS-007` | anon-denied | `a2a` | `401` | `anon` |
| `CS-008` | wrong-role-denied | `api` | `403` | `read-only` |
| `CS-009` | wrong-role-denied | `mcp` | `403` | `read-only` |
| `CS-010` | wrong-role-denied | `a2a` | `403` | `read-only` |
| `CS-011` | missing-param-error | `api` | `422` | `*` |
| `CS-012` | missing-param-error | `mcp` | `422` | `*` |
| `CS-013` | missing-param-error | `a2a` | `422` | `*` |

_These CS-NNN rows are pending W28C-1711 test binding. Each row binds to one or more `@pytest.mark.negative` tests with explicit expected denial code._


<!-- W28C-1711-R3 forensic: canonical FR-NNN rows derived from legacy R-NNN/FR1.NN test bindings (2026-06-15T15:21:28Z) -->

## Functional Requirements (W28C-1711-R3 canonical-FR expansion)

Per PS-REQ-TEST-TRACE §2: every test req() must reference a backtick-wrapped FR/CS/NF-NNN row. This section adds canonical FR-NNN rows derived from existing legacy R-NNN / FR1.NN bindings + ADD-REQ probe-test functional capabilities. Test bindings rewritten to use these canonical FR-NNN IDs.

| ID | Source (legacy) | Test count | Surface (inferred) | Priority | Description |
|---|---|---:|---|---|---|
| `FR-001` | R2 | 17 | `internal` | `should` | Functional capability covered by legacy binding `R2` (W28C-1711-R3 derivation; see new-or-updated-tests.tsv for test list) |


<!-- W28C-1711-R3 forensic: ADD-REQ FR rows derived from probe-test clusters (2026-06-15T15:21:28Z) -->

## Functional Requirements (W28C-1711-R3 ADD-REQ derivation)

Per W28C-1711 spec rule: ADD-REQ — create the requirement and bind the test. This section adds FR-NNN rows derived from functional probe-test clusters that had no matching FR in REQUIREMENTS.md. Each row's description is derived from the cluster's test names.

| ID | Cluster | Test count | Surface (inferred) | Priority | Description |
|---|---|---:|---|---|---|
| `FR-002` | unit | 43 | `internal` | `should` | Unit (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-003` | contract | 4 | `internal` | `should` | Contract (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-004` | application | 22 | `a2a,webui` | `should` | Application (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-005` | system | 18 | `internal` | `should` | System (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-006` | parser | 3 | `internal` | `should` | Parser (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-007` | integration | 42 | `a2a,api,cli,internal,webui` | `should` | Integration (W28C-1711-R3 ADD-REQ cluster derivation) |
| `FR-008` | security | 6 | `internal` | `should` | Security (W28C-1711-R3 ADD-REQ cluster derivation) |
