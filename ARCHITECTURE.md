# Index Retriever MCP Server Architecture

## 1. Purpose

`index-retriever-mcp-server` is the retrieval and indexing service for Cloud-Dog agent workflows. It exposes the same core capability set through:

- an HTTP API, which is the canonical integration surface,
- an MCP tool interface for agent-to-agent and tool-calling runtimes,
- A2A-compatible endpoints for platform interoperability,
- an Admin WebUI served by this runtime that consumes the HTTP API only.

The service owns the transport contracts, authentication and authorisation boundaries, tool catalogue, ingest and retrieval orchestration, audit hooks, and lightweight platform database state. It also delegates parser, OCR, table-extraction, and backend-capability planning to platform packages where appropriate.

This document is written for external technical users. It describes the delivered architecture in this repository as implemented and test-backed, not only the broader requirement intent.

## 2. Scope and Reader Guidance

This repository delivers and documents:

- API, MCP, and A2A runtime surfaces,
- a shared tool and service layer used by all transports,
- profile and collection administration,
- text ingestion, reference ingestion, search, retrieval, preview, OCR planning, table extraction, retention, and reindex operations,
- Vault-aware configuration loading,
- database initialisation and health checks,
- audit event emission,
- an in-repo admin WebUI under `/admin/ui/*`,
- containerised all-in-one runtime packaging.

This repository ships a lightweight Admin WebUI for profile, user, group, and API-key administration. The WebUI is intentionally thin and acts as a strict HTTP API client. It does not access DB, VDB, queue, or backend providers directly.

## 3. Architecture Summary

At a high level, the service is split into four layers:

1. **Transport layer**
   - FastAPI-based HTTP API
   - MCP server and MCP tool contract registration
   - A2A-compatible endpoints

2. **Application layer**
   - `IndexService` as the central orchestration facade
   - tool registry and transport-independent tool execution
   - RBAC enforcement and request shaping

3. **Capability layer**
   - parsing, OCR, and table extraction delegation through `cloud_dog_vdb`
   - embedding delegation through `cloud_dog_llm`
   - configuration through `cloud_dog_config`
   - database runtime through `cloud_dog_db`

4. **Runtime state layer**
   - lightweight service-owned relational state
   - in-process queue fallback
   - in-process vector storage fallback
   - append-only audit logging

The most important architectural detail for external users is this:

- The **public contracts are stable and multi-backend aware**.
- The **core in-repo runtime path currently uses an in-memory VDB adapter and an in-process queue fallback** for deterministic local and test behaviour.
- The **parser, OCR, table, and capability-planning paths are already delegated to platform packages and are validated against live matrices in the test suite**.

## 4. System Context

```mermaid
graph TB
    subgraph Clients
        REST[REST / HTTP clients]
        MCPCLIENT[MCP clients]
        A2A[A2A / agent runtimes]
        WEBUI[Admin WebUI<br/>external consumer]
    end

    subgraph Service
        IDX[index-retriever-mcp-server]
    end

    subgraph Platform Dependencies
        CFG[cloud_dog_config]
        IDAM[cloud_dog_idam]
        DB[cloud_dog_db]
        LLM[cloud_dog_llm]
        VDBPKG[cloud_dog_vdb]
        JOBS[cloud_dog_jobs]
        VAULT[Vault]
    end

    subgraph External Systems
        EMB[Embedding providers]
        PARSERS[Parser / OCR providers]
        SQL[(SQL database)]
        VDBS[(Vector backends)]
        STORAGE[Filesystem / S3 / WebDAV / FTP / GDrive]
    end

    REST --> IDX
    MCPCLIENT --> IDX
    A2A --> IDX
    WEBUI --> IDX

    IDX --> CFG
    IDX --> IDAM
    IDX --> DB
    IDX --> LLM
    IDX --> VDBPKG
    IDX --> JOBS
    IDX --> VAULT

    IDX --> EMB
    IDX --> PARSERS
    IDX --> SQL
    IDX --> VDBS
    IDX --> STORAGE
```

## 5. Runtime Topology

### 5.1 Transport topology

The runtime exposes these logical surfaces:

| Surface | Canonical path | Primary code |
|---|---|---|
| API | `/app/v1` | `src/index_server/api_server.py` |
| Legacy API alias | `/api/v1` | `src/index_server/api_server.py` |
| MCP | `/mcp` | `src/index_server/mcp_server.py` |
| A2A | `/a2a` | `src/index_server/api_server.py` |
| Health | `/health`, `/api/health`, `/app/v1/health` | `src/index_server/api_server.py` |

The MCP runtime is registered through `cloud_dog_api_kit.register_mcp_contract(...)`, with legacy tools alias support enabled for compatibility.

### 5.2 All-in-one container topology

The default container packaging starts API and MCP services and optionally bridges additional ports:

- API port: `CLOUD_DOG__INDEX__API_SERVER__PORT`
- MCP port: `CLOUD_DOG__INDEX__MCP_SERVER__PORT`
- Web compatibility port: `CLOUD_DOG__INDEX__WEB_SERVER__PORT`
- A2A compatibility port: `CLOUD_DOG__INDEX__A2A_SERVER__PORT`

In the all-in-one image, `docker-entrypoint.sh` can start compatibility TCP bridges:

- Web port -> API port
- A2A port -> API port

This gives stable external ports without duplicating application servers.

### 5.3 Runtime process view

```mermaid
graph LR
    ENTRY[docker-entrypoint.sh]
    CTRL[server_control.sh]
    API[API server]
    MCP[MCP server]
    BR1[web bridge]
    BR2[a2a bridge]

    ENTRY --> CTRL
    CTRL --> API
    CTRL --> MCP
    ENTRY --> BR1
    ENTRY --> BR2
```

## 6. Component Decomposition

```mermaid
graph TB
    subgraph Transport
        API[API app]
        MCP[MCP app]
        A2A[A2A handlers]
    end

    subgraph Application
        AUTH[Auth middleware]
        REG[Tool registry]
        EXEC[Tool dispatcher]
        SVC[IndexService]
    end

    subgraph Capability
        EMB[EmbeddingAdapter]
        SEARCH[SearchEngine]
        COLL[CollectionManager]
        PARSE[cloud_dog_vdb parser pipeline]
        OCR[cloud_dog_vdb OCR planner]
        CAP[cloud_dog_vdb capability planner]
    end

    subgraph Runtime State
        QUEUE[QueueEngine]
        VDB[InMemoryVdbAdapter]
        AUDIT[AuditLogger]
        DBRT[PlatformDatabaseRuntime]
    end

    API --> AUTH --> REG --> EXEC --> SVC
    MCP --> AUTH --> REG --> EXEC --> SVC
    A2A --> AUTH --> SVC

    SVC --> EMB
    SVC --> SEARCH
    SVC --> COLL
    SVC --> PARSE
    SVC --> OCR
    SVC --> CAP
    SVC --> QUEUE
    SEARCH --> VDB
    COLL --> VDB
    SVC --> AUDIT
    API --> DBRT
    MCP --> DBRT
```

### 6.1 Transport layer

The transport layer is intentionally thin:

- `src/index_server/api_server.py` builds the HTTP API and A2A endpoints.
- `src/index_server/mcp_server.py` builds the MCP server and registers tool contracts.
- Both surfaces route into the same `IndexService` and tool registry, so API and MCP behaviour stay aligned.

### 6.2 Shared tool layer

`src/index_tools/tools/registry.py` defines a schema-first tool registry. Each tool publishes:

- name,
- description,
- handler name,
- input JSON schema,
- output JSON schema.

This registry is used by both API and MCP surfaces, which is why the same tool set is available across transports.

### 6.3 Service layer

`src/index_tools/tools/service.py` is the main application facade. It owns:

- profile and collection operations,
- ingest orchestration,
- search and retrieval,
- parser and OCR helper flows,
- stream session ingestion,
- job inspection and retry hooks,
- retention and reindex actions,
- dependency health reporting.

## 7. Transport Contracts

### 7.1 HTTP API

The HTTP API is the canonical surface for external integrations and the Admin WebUI.

Implemented routes include:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | service health |
| `GET` | `/api/health` | compatibility health |
| `GET` | `/app/v1/health` | canonical API health |
| `GET` | `/a2a` | A2A descriptor |
| `GET` | `/a2a/health` | A2A health |
| `GET` | `/app/v1/tools` | list tools |
| `POST` | `/app/v1/tools/{tool_name}` | execute tool |
| `GET` | `/api/v1/tools` | legacy tool list |
| `POST` | `/api/v1/tools/{tool_name}` | legacy tool execute |

Health payloads include:

- overall status,
- correlation ID,
- database probe,
- vector backend health,
- embedding health.

### 7.2 MCP

The MCP runtime is built from the same tool registry. It exposes:

- `GET /health`
- canonical MCP tool contract at `/mcp`
- canonical MCP catalogue at `/mcp/tools`
- legacy alias support through the platform contract registration layer

Each tool call is authenticated and then dispatched through the same `execute_tool(...)` path used by the API.

### 7.3 A2A

The A2A surface is a small authenticated HTTP contract:

- `GET /a2a`
- `GET /a2a/health`

`/a2a/health` enforces the shared API-key authority and is expected to return:

- `401` without valid credentials,
- `200` with a valid API key supplied either as `X-API-Key` or `Authorization: Bearer <api-key>`.

### 7.4 Tool catalogue and execution coverage

The shared tool registry publishes the service catalogue and JSON schemas for both API and MCP clients.

The registry currently advertises these tool families:

- profile and collection tools,
- ingest and stream tools,
- parser, preview, OCR, and table tools,
- search and retrieval tools,
- job and queue tools,
- maintenance and health tools.

Concrete dispatcher paths are implemented today for:

- `profiles_list`
- `profile_get`
- `collections_list`
- `admin_collection_create`
- `admin_collection_delete`
- `ingest_text`
- `parsers_list`
- `parser_test`
- `ingest_preview`
- `extract_only`
- `ocr_run`
- `table_extract`
- `search`
- `job_get`
- `job_wait`
- `job_list`
- `job_cancel`
- `job_retry`
- `backend_health_check`
- `embedding_health_check`
- `queue_status`

The registry also contains compatibility-facing names beyond that concrete dispatch subset. External users should therefore treat the tool catalogue as the declared contract surface, but validate any operation they depend on against the corresponding test coverage and current runtime behaviour.

## 8. Authentication, Authorisation, and Audit

### 8.1 Authentication

Authentication is handled by `src/index_server/auth/middleware.py`.

Delivered behaviour:

- API keys are loaded from `CLOUD_DOG__INDEX__AUTH__API_KEYS`.
- `TEST_A2A_API_KEY` is also supported for strict A2A contract tests.
- API keys are accepted from either:
  - `X-API-Key`
  - `Authorization: Bearer <api-key>`
- Local fixed bearer tokens are supported for deterministic role tests:
  - `valid-reader-token`
  - `valid-writer-token`
  - `valid-admin-token`

When the platform identity package is available, auth health reports `cloud_dog_idam`; otherwise the local fallback path reports `fallback`.

### 8.2 Authorisation

The role model enforced across transports is:

- `reader`
- `writer`
- `maintainer`
- `admin`

Authorisation is enforced:

- per transport request,
- per tool category,
- and, where configured, per collection through collection ACL checks.

Examples:

- admin tools require `admin`,
- ingest tools require `writer`, `maintainer`, or `admin`,
- parser test, OCR, and table extraction require `maintainer` or `admin`,
- search and retrieve are available to `reader` and above.

### 8.3 Audit

Audit events are emitted through `AuditLogger`. API and MCP can use separate audit paths resolved from environment configuration:

- `CLOUD_DOG__INDEX__API_AUDIT_PATH`
- `CLOUD_DOG__INDEX__MCP_AUDIT_PATH`
- `CLOUD_DOG__INDEX__STORAGE__AUDIT__PATH`
- `AUDIT_LOG_PATH`

The architecture guarantees that transport entry points pass actor identity into service operations so audit events can capture the caller.

## 9. Data and State Model

### 9.1 Database-owned state

This repository owns a lightweight relational schema through `cloud_dog_db` migrations.

Current service-owned ORM model:

- `IndexPlatformDbState`

This table proves service schema ownership and supports database startup and migration verification. It should be understood as platform runtime state, not as the primary document store.

### 9.2 In-memory operational state

The current in-repo service runtime holds several operational structures in memory:

- collections and documents in `InMemoryVdbAdapter`,
- jobs in `QueueEngine`,
- profile definitions in `IndexService.profiles`,
- collection ACLs in `IndexService.collection_roles`,
- stream sessions in `IndexService.stream_sessions`,
- ingested document records in `IndexService.documents`,
- idempotency keys in `IndexService.idempotency`.

This is a deliberate implementation boundary today and should be factored into deployment expectations.

### 9.3 Database runtime integration

`src/index_tools/db/runtime.py` provides:

- environment-driven SQL settings resolution,
- sync-driver normalisation for async DSNs,
- automatic migration execution from `database/migrations/cloud_dog_db`,
- connection health probing,
- engine lifecycle management.

Default local persistence uses SQLite at `./data/index_retriever.db` unless overridden by environment variables.

## 10. Ingestion and Retrieval Architecture

### 10.1 Standard ingest path

For `ingest_text`, the main runtime flow is:

1. validate profile,
2. ensure collection exists,
3. generate an idempotency key,
4. create a job record,
5. chunk input text with `token_chunks`,
6. generate embeddings through `EmbeddingAdapter`,
7. upsert chunks into `InMemoryVdbAdapter`,
8. persist an in-memory `DocumentRecord`,
9. write audit events,
10. mark the in-process job complete.

```mermaid
sequenceDiagram
    participant C as Client
    participant T as API or MCP
    participant S as IndexService
    participant Q as QueueEngine
    participant E as EmbeddingAdapter
    participant V as InMemoryVdbAdapter
    participant A as AuditLogger

    C->>T: ingest_text
    T->>S: validated request
    S->>Q: enqueue job
    S->>E: embed chunks
    E-->>S: vectors
    S->>V: upsert document chunks
    S->>A: write ingest audit event
    S-->>T: job_id and status
    T-->>C: response
```

### 10.2 Reference ingest path

`ingest_reference` currently reads a local path and reuses the text-ingest path. Connector modules for filesystem, S3, WebDAV, FTP, HTTP, and Google Drive exist in the repository and are unit-tested, but the primary service method in this repository currently implements local-path reference ingestion directly.

This distinction matters for external users:

- connector capability exists at module level,
- contract and configuration support exists in requirements and tests,
- the delivered main service path for `ingest_reference` is still the simpler local-path implementation.

### 10.3 Search and retrieval path

The search path uses two steps:

1. build a backend capability plan through `cloud_dog_vdb` when available,
2. execute the actual query through `SearchEngine`, which currently uses `InMemoryVdbAdapter`.

Current query scoring in the in-memory adapter is overlap-based text scoring over stored chunks, not a live remote vector query.

`retrieve` returns the stored document text and metadata from the in-memory document map.

### 10.4 Stream ingest path

Streaming helpers in `src/index_server/streaming.py` expose the session lifecycle:

- `ingest_stream_open`
- `ingest_stream_event`
- `ingest_stream_close`

The service keeps per-session stream state in memory and turns each event into the same underlying ingest flow used for text ingestion.

### 10.5 Maintenance operations

The service also exposes:

- `delete_by_id`
- `delete_by_filter`
- `retention_run`
- `reindex_run`

These operate against the same runtime document and collection state used by the current service implementation.

## 11. Parser, OCR, and Table-Extraction Architecture

### 11.1 Delegation model

Parser and OCR flows are intentionally delegated to `cloud_dog_vdb` rather than being hard-coded in the service.

The service uses platform package entry points for:

- parser registry construction,
- ingestion preview,
- extract-only flows,
- OCR planner decisions,
- table extraction flows,
- backend capability planning.

This means the parsing plane is already externalised even though the primary search and queue runtime in this repository is still local and in-process.

### 11.2 Delivered parser-facing operations

The main parser-facing tools are:

- `parsers_list`
- `parser_test`
- `ingest_preview`
- `extract_only`
- `ocr_run`
- `table_extract`

These operations let external users:

- discover parser providers,
- validate parser health,
- preview chunking and extraction results before indexing,
- evaluate OCR decisions,
- extract table structures without full ingestion.

### 11.3 Verified parser provider matrix

The test plan defines and exercises parser-provider coverage for:

- DeepDoc
- Docling
- MinerU
- Marker MCP
- Transformers
- Internal

The corresponding integration suites are `IT2.7` through `IT2.12`, with OCR matrix coverage in `IT2.13` and table extraction matrix coverage in `IT2.14`.

## 12. Vector Backend and Embedding Architecture

### 12.1 Current runtime behaviour

Within this repository, the main `IndexService` currently writes and queries through `InMemoryVdbAdapter`.

That adapter provides:

- collection creation and deletion,
- chunk upsert,
- metadata filter matching,
- simple overlap-based query scoring,
- embedding dimension consistency validation,
- lightweight health reporting.

This is the current service-core runtime path.

### 12.2 Backend capability model

The broader backend model is defined through `cloud_dog_vdb` capability descriptors and planning. The repository’s requirements and tests validate cross-backend expectations even when the default local runtime path remains in-process.

Backends covered by the contract and integration matrix are:

- Chroma
- Qdrant
- OpenSearch
- PGVector
- Weaviate
- Infinity

Relevant suites include:

- `CT1.1` to `CT1.4`
- `IT2.1` to `IT2.6`
- `AT2.1`, `AT2.2`, `AT2.5`
- `PT1.1`, `PT1.2`

### 12.3 Embedding architecture

Embeddings are produced through `EmbeddingAdapter`, which delegates to `cloud_dog_llm` when available.

Provider configuration is controlled by:

- `CLOUD_DOG__INDEX__EMBEDDING__PROVIDER`
- `CLOUD_DOG__INDEX__EMBEDDING__MODEL`

If the platform package is not available, a deterministic local fallback embedding is generated from a SHA-256 digest. This fallback exists for deterministic local and test behaviour and should not be treated as the target production embedding path.

The multi-model application matrix covers:

- BGE
- Nomic
- Granite

through `AT2.4`.

## 13. Queue and Job Architecture

`QueueEngine` currently provides the in-process queue fallback used by the service core.

Delivered behaviour:

- job enqueue,
- job lookup,
- job listing,
- synchronous execution,
- retry hook support,
- idempotency key generation.

When `cloud_dog_jobs` is importable, queue health can report that backend name. The current service implementation, however, still executes jobs synchronously in-process for deterministic behaviour.

For external users, this means:

- the API and tool contracts for jobs are stable,
- the current default runtime is not a distributed worker topology,
- queue semantics can evolve behind the same external tool contract.

## 14. Configuration and Secret Resolution

Configuration is loaded through `cloud_dog_config.load_config(...)` in `src/index_tools/config/loader.py`.

Documented precedence is:

1. `os.environ`
2. `.env` or explicit env files
3. `config.yaml`
4. `defaults.yaml`
5. Vault-backed resolution

This repository expects runtime configuration to converge into a single typed `GlobalConfig`.

Important characteristics:

- Vault resolution is supported by the canonical loader path.
- unresolved values can be treated strictly,
- backward-compatible merge logic exists for direct unit-test layer injection,
- runtime code should read from environment-driven or loaded configuration, not hard-coded values.

## 15. Deployment Model

### 15.1 Local and test tiers

The project ships a large environment and test harness set for:

- UT
- ST
- IT
- AT
- PT
- local Docker all-in-one runtime

These harnesses are used to validate:

- route contracts,
- auth contracts,
- parser/provider matrices,
- backend matrices,
- database startup and migration,
- end-to-end ingest and search flows.

### 15.2 Pre-production and production

For external deployments, the intended topology is:

- this service container,
- SQL database,
- embedding provider,
- parser and OCR providers as required,
- one or more configured vector backends,
- Vault or equivalent secret source.

The shipped `env-docker-example` and container entrypoint provide the all-in-one runtime baseline, while host-network or explicit port publishing can be layered around it at deployment time.

## 16. Verification and Traceability

The architecture described here is backed by three inputs:

1. requirements in `REQUIREMENTS.md`,
2. implementation in `src/`,
3. tiered verification in `TESTS.md` and `tests/`.

Examples of test-backed architecture claims:

| Capability | Evidence |
|---|---|
| canonical API and MCP route contract | `IT1.1` to `IT1.18`, route-prefix strict runs in `TESTS.md` |
| A2A auth parity | `IT1.18`, `UT1.38`, W14B strict evidence in `TESTS.md` |
| admin WebUI API-only CRUD path | `AT1.10`, `IT1.22`, `UT1.44` |
| DB startup and migration | `ST1.14`, `IT2.15` |
| parser provider matrix | `IT2.7` to `IT2.14`, `AT2.3`, `PT1.3` |
| six-backend VDB matrix | `CT1.1` to `CT1.4`, `IT2.1` to `IT2.6`, `AT2.1`, `AT2.2`, `AT2.5` |
| multi-embedding model verification | `AT2.4` |
| tool schema and dispatch integrity | `UT1.29`, `UT1.37`, `UT1.40` |

## 17. Current Implementation Boundaries

External users should be aware of the following current boundaries:

1. The packaged Admin WebUI currently covers profile, user, group, and API-key administration. Broader observability and document workflow screens remain outside this in-repo UI surface.
2. The current service-core indexing and search path uses `InMemoryVdbAdapter`, not a live remote VDB client inside `IndexService`.
3. The current service-core queue path uses synchronous in-process execution through `QueueEngine`.
4. `ingest_reference` currently handles local path references directly; connector modules exist separately and are not yet the sole orchestrated path inside `IndexService`.
5. The relational schema owned by this repository is intentionally small and does not currently act as the primary document or job store.

These are implementation facts, not documentation gaps. They should be used to plan deployment and integration expectations correctly.

## 18. External Integration Guidance

For external integrators, the recommended stable integration choices are:

- use the HTTP API under `/app/v1` as the primary contract,
- use `/mcp` when integrating from MCP-aware clients,
- use `/a2a` only when you need agent interoperability contracts,
- rely on the tool catalogue rather than transport-specific custom paths,
- treat parser and backend selection as configuration concerns,
- validate target parser and backend combinations with the corresponding IT and AT suites before promotion.

## 19. Source of Truth

When this document and code appear to differ, the source-of-truth order is:

1. transport and service implementation in `src/`,
2. requirement obligations in `REQUIREMENTS.md`,
3. test-backed verified behaviour in `tests/` and `TESTS.md`,
4. this document.

This document has been updated to match that source-of-truth order.
