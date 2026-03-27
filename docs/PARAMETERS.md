# Configuration Parameters

All parameters can be set via `defaults.yaml`, `config.yaml`, environment variables, or Vault.

## Server Ports

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| api_server.host | 0.0.0.0 | - | API server bind address |
| api_server.port | 8074 | - | API server port |
| web_server.host | 0.0.0.0 | - | Web server bind address |
| web_server.port | 8075 | - | Web server port |
| mcp_server.host | 0.0.0.0 | - | MCP server bind address |
| mcp_server.port | 8076 | - | MCP server port |
| mcp_server.transport | streamable-http | - | MCP transport mode |
| a2a_server.host | 0.0.0.0 | - | A2A server bind address |
| a2a_server.port | 8077 | - | A2A server port |

## Authentication

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| auth.mode | apikey+jwt | - | Auth mode (apikey+jwt, api_key, jwt) |
| auth.jwt.issuer | (empty) | JWT_ISSUER | JWT token issuer |
| auth.jwt.audience | (empty) | JWT_AUDIENCE | JWT token audience |
| auth.jwt.public_keys_url | (empty) | JWT_JWKS_URL | JWKS public keys URL |

## Storage

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| storage.db.url | sqlite+aiosqlite:///./data/index_retriever.db | DB_URL | Database connection URL |
| storage.audit.path | ./logs/audit.log | AUDIT_LOG_PATH | Audit log file path |

## Queue

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| queue.backend | sql | CLOUD_DOG__INDEX__QUEUE__BACKEND | Queue backend type |
| queue.database_url | (from DB_URL) | INDEX_RETRIEVER_DB_URL | Queue database URL |
| queue.server_id | index-retriever-local | INDEX_RETRIEVER_SERVER_ID / HOSTNAME | Server identifier |
| queue.max_concurrency | 8 | - | Max concurrent queue workers |
| queue.per_profile_concurrency | 2 | - | Max workers per profile |
| queue.default_timeout_seconds | 1800 | - | Default job timeout |
| queue.retry.max_attempts | 3 | - | Max retry attempts |
| queue.retry.backoff_seconds | 5 | - | Retry backoff |
| queue.redis.enabled | false | - | Enable Redis queue |
| queue.redis.url | redis://127.0.0.1:6379/0 | REDIS_URL | Redis URL |

## Profiles

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.enabled | true | - | Enable the default profile |

### VDB (Vector Database)

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.vdb.type | chroma | - | VDB backend (chroma) |
| profiles.default.vdb.chroma.mode | local | - | Chroma mode (local, remote) |
| profiles.default.vdb.chroma.path | ./data/chroma | CHROMA_PATH | Chroma data path |
| profiles.default.vdb.chroma.collection | default | - | Default collection name |

### Embeddings

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.embeddings.provider | openai_compat | - | Embedding provider |
| profiles.default.embeddings.openai_compat.base_url | https://llm1.cloud-dog.net | EMBED_BASE_URL | Embedding API URL |
| profiles.default.embeddings.openai_compat.api_key | (empty) | EMBED_API_KEY | Embedding API key |
| profiles.default.embeddings.openai_compat.model | nomic-embed-text | - | Embedding model name |
| profiles.default.embeddings.openai_compat.timeout_seconds | 60 | - | Embedding timeout |

### Ingestion

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.ingestion.allowed_sources | [upload, text, filesystem, s3, webdav, gdrive] | - | Allowed ingestion sources |
| profiles.default.ingestion.filesystem.roots | [./uploads] | INGEST_ROOT | Filesystem ingestion roots |
| profiles.default.ingestion.filesystem.deny_globs | [**/.git/**, **/node_modules/**] | - | Denied paths |
| profiles.default.ingestion.max_file_mb | 50 | - | Max file size (MB) |
| profiles.default.ingestion.dedupe.mode | hash | - | Deduplication mode |
| profiles.default.ingestion.dedupe.policy | skip | - | Dedupe policy (skip, replace, version) |

### Chunking

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.chunking.strategy | token | - | Chunking strategy |
| profiles.default.chunking.chunk_size | 800 | - | Chunk size (tokens) |
| profiles.default.chunking.chunk_overlap | 100 | - | Chunk overlap (tokens) |

### Search

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| profiles.default.search.top_k_default | 10 | - | Default top-k results |
| profiles.default.search.score_threshold | 0.0 | - | Minimum score threshold |

## RBAC

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| rbac.enabled | true | - | Enable RBAC |
| rbac.default_deny | true | - | Default deny if no role matches |
| rbac.roles.admin | ["*"] | - | Admin permissions |
| rbac.roles.maintainer | [profiles_*, collections_*, ingest_*, search, ...] | - | Maintainer permissions |
| rbac.roles.writer | [ingest_*, search, retrieve, job_*, queue_status] | - | Writer permissions |
| rbac.roles.reader | [profiles_list, collections_list, search, retrieve, ...] | - | Reader permissions |

## Logging

| Parameter | Default | Env Override | Description |
|-----------|---------|-------------|-------------|
| log.service_instance | index-retriever-local | HOSTNAME | Service instance ID |
| log.environment | dev | CLOUD_DOG_ENVIRONMENT | Deployment environment |
| log.retention.hot_days | 14 | - | Days to keep hot logs |
| log.retention.cold_days | 60 | - | Days to keep archived logs |
| log.retention.archive_format | gz | - | Archive compression format |
| log.integrity.enabled | true | - | Enable log integrity checks |
| log.integrity.interval_seconds | 300 | - | Integrity check interval |
| log.integrity.hash_algorithm | sha256 | - | Hash algorithm |
| log.rotation.mode | size | - | Rotation mode |
| log.rotation.max_bytes | 104857600 | - | Max bytes before rotation |
| log.rotation.backup_count | 10 | - | Rotated file count |
| log.rotation.compress | true | - | Compress rotated files |
