# Parameters

This reference is generated from `defaults.yaml`. Each key can be overridden by the corresponding environment variable.

## `a2a_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `a2a_server.host` | `0.0.0.0` | `CLOUD_DOG__A2A_SERVER__HOST` | Host binding or upstream host for a2a server. |
| `a2a_server.port` | `8077` | `CLOUD_DOG__A2A_SERVER__PORT` | Port for a2a server connections. |

## `api_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `api_server.host` | `0.0.0.0` | `CLOUD_DOG__API_SERVER__HOST` | Host binding or upstream host for api server. |
| `api_server.port` | `8074` | `CLOUD_DOG__API_SERVER__PORT` | Port for api server connections. |

## `auth`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `auth.mode` | `apikey+jwt` | `CLOUD_DOG__AUTH__MODE` | Configuration value for auth mode. |
| `auth.jwt.issuer` | `${JWT_ISSUER || ''}` | `CLOUD_DOG__AUTH__JWT__ISSUER` | Configuration value for auth jwt issuer. |
| `auth.jwt.audience` | `${JWT_AUDIENCE || ''}` | `CLOUD_DOG__AUTH__JWT__AUDIENCE` | Configuration value for auth jwt audience. |
| `auth.jwt.public_keys_url` | `${JWT_JWKS_URL || ''}` | `CLOUD_DOG__AUTH__JWT__PUBLIC_KEYS_URL` | Endpoint or connection URL for auth jwt public keys. |

## `log`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `log.service_instance` | `${HOSTNAME:index-retriever-local}` | `CLOUD_DOG__LOG__SERVICE_INSTANCE` | Configuration value for log service instance. |
| `log.environment` | `${CLOUD_DOG_ENVIRONMENT:dev}` | `CLOUD_DOG__LOG__ENVIRONMENT` | Configuration value for log environment. |
| `log.retention.hot_days` | `14` | `CLOUD_DOG__LOG__RETENTION__HOT_DAYS` | Configuration value for log retention hot days. |
| `log.retention.cold_days` | `60` | `CLOUD_DOG__LOG__RETENTION__COLD_DAYS` | Configuration value for log retention cold days. |
| `log.retention.archive_format` | `gz` | `CLOUD_DOG__LOG__RETENTION__ARCHIVE_FORMAT` | Configuration value for log retention archive format. |
| `log.integrity.enabled` | `true` | `CLOUD_DOG__LOG__INTEGRITY__ENABLED` | Toggle for log integrity. |
| `log.integrity.interval_seconds` | `300` | `CLOUD_DOG__LOG__INTEGRITY__INTERVAL_SECONDS` | Timeout or duration control for log integrity interval. |
| `log.integrity.log_file` | `logs/audit-integrity.log` | `CLOUD_DOG__LOG__INTEGRITY__LOG_FILE` | Configuration value for log integrity log file. |
| `log.integrity.hash_algorithm` | `sha256` | `CLOUD_DOG__LOG__INTEGRITY__HASH_ALGORITHM` | Configuration value for log integrity hash algorithm. |
| `log.rotation.mode` | `size` | `CLOUD_DOG__LOG__ROTATION__MODE` | Configuration value for log rotation mode. |
| `log.rotation.max_bytes` | `104857600` | `CLOUD_DOG__LOG__ROTATION__MAX_BYTES` | Configuration value for log rotation max bytes. |
| `log.rotation.backup_count` | `10` | `CLOUD_DOG__LOG__ROTATION__BACKUP_COUNT` | Configuration value for log rotation backup count. |
| `log.rotation.when` | `midnight` | `CLOUD_DOG__LOG__ROTATION__WHEN` | Configuration value for log rotation when. |
| `log.rotation.interval` | `1` | `CLOUD_DOG__LOG__ROTATION__INTERVAL` | Configuration value for log rotation interval. |
| `log.rotation.compress` | `true` | `CLOUD_DOG__LOG__ROTATION__COMPRESS` | Configuration value for log rotation compress. |

## `mcp_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `mcp_server.host` | `0.0.0.0` | `CLOUD_DOG__MCP_SERVER__HOST` | Host binding or upstream host for mcp server. |
| `mcp_server.port` | `8076` | `CLOUD_DOG__MCP_SERVER__PORT` | Port for mcp server connections. |
| `mcp_server.transport` | `streamable-http` | `CLOUD_DOG__MCP_SERVER__TRANSPORT` | Configuration value for mcp server transport. |

## `profiles`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `profiles.default.enabled` | `true` | `CLOUD_DOG__PROFILES__DEFAULT__ENABLED` | Toggle for profiles default. |
| `profiles.default.vdb.type` | `chroma` | `CLOUD_DOG__PROFILES__DEFAULT__VDB__TYPE` | Configuration value for profiles default vdb type. |
| `profiles.default.vdb.chroma.mode` | `local` | `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__MODE` | Configuration value for profiles default vdb chroma mode. |
| `profiles.default.vdb.chroma.path` | `${CHROMA_PATH:./data/chroma}` | `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__PATH` | Configuration value for profiles default vdb chroma path. |
| `profiles.default.vdb.chroma.collection` | `default` | `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__COLLECTION` | Configuration value for profiles default vdb chroma collection. |
| `profiles.default.embeddings.provider` | `openai_compat` | `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__PROVIDER` | Configuration value for profiles default embeddings provider. |
| `profiles.default.embeddings.openai_compat.base_url` | `<set per environment>` | `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__BASE_URL` | Endpoint or connection URL for profiles default embeddings openai compat base. |
| `profiles.default.embeddings.openai_compat.api_key` | `<secret>` | `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__API_KEY` | Credential or authentication setting for the related subsystem. |
| `profiles.default.embeddings.openai_compat.model` | `nomic-embed-text` | `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__MODEL` | Configuration value for profiles default embeddings openai compat model. |
| `profiles.default.embeddings.openai_compat.timeout_seconds` | `60` | `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__TIMEOUT_SECONDS` | Timeout or duration control for profiles default embeddings openai compat timeout. |
| `profiles.default.ingestion.allowed_sources` | `["upload", "text", "filesystem", "s3", "webdav", "gdrive"]` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__ALLOWED_SOURCES` | Configuration value for profiles default ingestion allowed sources. |
| `profiles.default.ingestion.filesystem.roots` | `["${INGEST_ROOT:./uploads}"]` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__FILESYSTEM__ROOTS` | Configuration value for profiles default ingestion filesystem roots. |
| `profiles.default.ingestion.filesystem.deny_globs` | `["**/.git/**", "**/node_modules/**"]` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__FILESYSTEM__DENY_GLOBS` | Configuration value for profiles default ingestion filesystem deny globs. |
| `profiles.default.ingestion.max_file_mb` | `50` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__MAX_FILE_MB` | Configuration value for profiles default ingestion max file mb. |
| `profiles.default.ingestion.dedupe.mode` | `hash` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__DEDUPE__MODE` | Configuration value for profiles default ingestion dedupe mode. |
| `profiles.default.ingestion.dedupe.policy` | `skip` | `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__DEDUPE__POLICY` | Configuration value for profiles default ingestion dedupe policy. |
| `profiles.default.chunking.strategy` | `token` | `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__STRATEGY` | Configuration value for profiles default chunking strategy. |
| `profiles.default.chunking.chunk_size` | `800` | `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__CHUNK_SIZE` | Configuration value for profiles default chunking chunk size. |
| `profiles.default.chunking.chunk_overlap` | `100` | `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__CHUNK_OVERLAP` | Configuration value for profiles default chunking chunk overlap. |
| `profiles.default.search.top_k_default` | `10` | `CLOUD_DOG__PROFILES__DEFAULT__SEARCH__TOP_K_DEFAULT` | Configuration value for profiles default search top k default. |
| `profiles.default.search.score_threshold` | `0.0` | `CLOUD_DOG__PROFILES__DEFAULT__SEARCH__SCORE_THRESHOLD` | Configuration value for profiles default search score threshold. |

## `queue`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `queue.backend` | `${CLOUD_DOG__INDEX__QUEUE__BACKEND:sql}` | `CLOUD_DOG__QUEUE__BACKEND` | Configuration value for queue backend. |
| `queue.database_url` | `${INDEX_RETRIEVER_DB_URL:${DB_URL:sqlite+aiosqlite:///./data/...` | `CLOUD_DOG__QUEUE__DATABASE_URL` | Endpoint or connection URL for queue database. |
| `queue.server_id` | `${INDEX_RETRIEVER_SERVER_ID:${HOSTNAME:index-retriever-local}}` | `CLOUD_DOG__QUEUE__SERVER_ID` | Configuration value for queue server id. |
| `queue.max_concurrency` | `8` | `CLOUD_DOG__QUEUE__MAX_CONCURRENCY` | Configuration value for queue max concurrency. |
| `queue.per_profile_concurrency` | `2` | `CLOUD_DOG__QUEUE__PER_PROFILE_CONCURRENCY` | Configuration value for queue per profile concurrency. |
| `queue.default_timeout_seconds` | `1800` | `CLOUD_DOG__QUEUE__DEFAULT_TIMEOUT_SECONDS` | Timeout or duration control for queue default timeout. |
| `queue.retry.max_attempts` | `3` | `CLOUD_DOG__QUEUE__RETRY__MAX_ATTEMPTS` | Configuration value for queue retry max attempts. |
| `queue.retry.backoff_seconds` | `5` | `CLOUD_DOG__QUEUE__RETRY__BACKOFF_SECONDS` | Timeout or duration control for queue retry backoff. |
| `queue.redis.enabled` | `false` | `CLOUD_DOG__QUEUE__REDIS__ENABLED` | Toggle for queue redis. |
| `queue.redis.url` | `${REDIS_URL:redis://127.0.0.1:6379/0}` | `CLOUD_DOG__QUEUE__REDIS__URL` | Endpoint or connection URL for queue redis. |

## `rbac`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `rbac.enabled` | `true` | `CLOUD_DOG__RBAC__ENABLED` | Toggle for rbac. |
| `rbac.default_deny` | `true` | `CLOUD_DOG__RBAC__DEFAULT_DENY` | Configuration value for rbac default deny. |
| `rbac.roles.admin` | `["*"]` | `CLOUD_DOG__RBAC__ROLES__ADMIN` | Configuration value for rbac roles admin. |
| `rbac.roles.maintainer` | `["profiles_*", "collections_*", "ingest_*", "search", "retrieve", "delete_*", "retention_*", "reindex_*", "job_*", "queu...` | `CLOUD_DOG__RBAC__ROLES__MAINTAINER` | Configuration value for rbac roles maintainer. |
| `rbac.roles.writer` | `["ingest_*", "search", "retrieve", "job_list", "job_get", "job_wait", "job_stream", "queue_status"]` | `CLOUD_DOG__RBAC__ROLES__WRITER` | Configuration value for rbac roles writer. |
| `rbac.roles.reader` | `["profiles_list", "profile_get", "collections_list", "collection_get", "search", "retrieve", "search_explain", "job_get"...` | `CLOUD_DOG__RBAC__ROLES__READER` | Configuration value for rbac roles reader. |

## `storage`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `storage.db.url` | `${DB_URL:sqlite+aiosqlite:///./data/index_retriever.db}` | `CLOUD_DOG__STORAGE__DB__URL` | Endpoint or connection URL for storage db. |
| `storage.audit.path` | `${AUDIT_LOG_PATH:./logs/audit.log}` | `CLOUD_DOG__STORAGE__AUDIT__PATH` | Configuration value for storage audit path. |

## `web_server`

| Key | Default | Environment Override | Description |
|-----|---------|----------------------|-------------|
| `web_server.host` | `0.0.0.0` | `CLOUD_DOG__WEB_SERVER__HOST` | Host binding or upstream host for web server. |
| `web_server.port` | `8075` | `CLOUD_DOG__WEB_SERVER__PORT` | Port for web server connections. |
