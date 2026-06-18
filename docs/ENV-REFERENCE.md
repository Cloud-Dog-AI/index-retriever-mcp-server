---
template-id: T-ENV
template-version: 1.0
applies-to: docs/ENV-REFERENCE.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 16fd5b2c0000000000000000000000000000000000
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T00:00:00Z
---

# Environment Reference

This reference is generated from `defaults.yaml` and the standard Cloud-Dog environment override pattern.

## `a2a_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__A2A_SERVER__HOST` | `0.0.0.0` | Optional | `0.0.0.0` | Host binding or upstream host for a2a server. |
| `CLOUD_DOG__A2A_SERVER__PORT` | `8077` | Optional | `8077` | Port for a2a server connections. |

## `api_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__API_SERVER__HOST` | `0.0.0.0` | Optional | `0.0.0.0` | Host binding or upstream host for api server. |
| `CLOUD_DOG__API_SERVER__PORT` | `8074` | Optional | `8074` | Port for api server connections. |

## `auth`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__AUTH__MODE` | `apikey+jwt` | Optional | `apikey+jwt` | Configuration value for auth mode. |
| `CLOUD_DOG__AUTH__JWT__ISSUER` | `${JWT_ISSUER || ''}` | Optional | `${JWT_ISSUER || ''}` | Configuration value for auth jwt issuer. |
| `CLOUD_DOG__AUTH__JWT__AUDIENCE` | `${JWT_AUDIENCE || ''}` | Optional | `${JWT_AUDIENCE || ''}` | Configuration value for auth jwt audience. |
| `CLOUD_DOG__AUTH__JWT__PUBLIC_KEYS_URL` | `${JWT_JWKS_URL || ''}` | Deployment dependent | `${JWT_JWKS_URL || ''}` | Endpoint or connection URL for auth jwt public keys. |

## `log`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__LOG__SERVICE_INSTANCE` | `${HOSTNAME:index-retriever-local}` | Optional | `${HOSTNAME:index-retriever-local}` | Configuration value for log service instance. |
| `CLOUD_DOG__LOG__ENVIRONMENT` | `${CLOUD_DOG_ENVIRONMENT:dev}` | Optional | `${CLOUD_DOG_ENVIRONMENT:dev}` | Configuration value for log environment. |
| `CLOUD_DOG__LOG__RETENTION__HOT_DAYS` | `14` | Optional | `14` | Configuration value for log retention hot days. |
| `CLOUD_DOG__LOG__RETENTION__COLD_DAYS` | `60` | Optional | `60` | Configuration value for log retention cold days. |
| `CLOUD_DOG__LOG__RETENTION__ARCHIVE_FORMAT` | `gz` | Optional | `gz` | Configuration value for log retention archive format. |
| `CLOUD_DOG__LOG__INTEGRITY__ENABLED` | `true` | Optional | `true` | Toggle for log integrity. |
| `CLOUD_DOG__LOG__INTEGRITY__INTERVAL_SECONDS` | `300` | Optional | `300` | Timeout or duration control for log integrity interval. |
| `CLOUD_DOG__LOG__INTEGRITY__LOG_FILE` | `logs/audit-integrity.log` | Optional | `logs/audit-integrity.log` | Configuration value for log integrity log file. |
| `CLOUD_DOG__LOG__INTEGRITY__HASH_ALGORITHM` | `sha256` | Optional | `sha256` | Configuration value for log integrity hash algorithm. |
| `CLOUD_DOG__LOG__ROTATION__MODE` | `size` | Optional | `size` | Configuration value for log rotation mode. |
| `CLOUD_DOG__LOG__ROTATION__MAX_BYTES` | `104857600` | Optional | `104857600` | Configuration value for log rotation max bytes. |
| `CLOUD_DOG__LOG__ROTATION__BACKUP_COUNT` | `10` | Optional | `10` | Configuration value for log rotation backup count. |
| `CLOUD_DOG__LOG__ROTATION__WHEN` | `midnight` | Optional | `midnight` | Configuration value for log rotation when. |
| `CLOUD_DOG__LOG__ROTATION__INTERVAL` | `1` | Optional | `1` | Configuration value for log rotation interval. |
| `CLOUD_DOG__LOG__ROTATION__COMPRESS` | `true` | Optional | `true` | Configuration value for log rotation compress. |

## `mcp_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__MCP_SERVER__HOST` | `0.0.0.0` | Optional | `0.0.0.0` | Host binding or upstream host for mcp server. |
| `CLOUD_DOG__MCP_SERVER__PORT` | `8076` | Optional | `8076` | Port for mcp server connections. |
| `CLOUD_DOG__MCP_SERVER__TRANSPORT` | `streamable-http` | Optional | `streamable-http` | Configuration value for mcp server transport. |

## `profiles`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__PROFILES__DEFAULT__ENABLED` | `true` | Optional | `true` | Toggle for profiles default. |
| `CLOUD_DOG__PROFILES__DEFAULT__VDB__TYPE` | `chroma` | Optional | `chroma` | Configuration value for profiles default vdb type. |
| `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__MODE` | `local` | Optional | `local` | Configuration value for profiles default vdb chroma mode. |
| `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__PATH` | `${CHROMA_PATH:./data/chroma}` | Optional | `./data/service.dat` | Configuration value for profiles default vdb chroma path. |
| `CLOUD_DOG__PROFILES__DEFAULT__VDB__CHROMA__COLLECTION` | `default` | Optional | `default` | Configuration value for profiles default vdb chroma collection. |
| `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__PROVIDER` | `openai_compat` | Optional | `openai_compat` | Configuration value for profiles default embeddings provider. |
| `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__BASE_URL` | `<set per environment>` | Deployment dependent | `<set per environment>` | Endpoint or connection URL for profiles default embeddings openai compat base. |
| `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__API_KEY` | `<secret>` | Deployment dependent | `your-api-key` | Credential or authentication setting for the related subsystem. |
| `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__MODEL` | `nomic-embed-text` | Optional | `nomic-embed-text` | Configuration value for profiles default embeddings openai compat model. |
| `CLOUD_DOG__PROFILES__DEFAULT__EMBEDDINGS__OPENAI_COMPAT__TIMEOUT_SECONDS` | `60` | Optional | `60` | Timeout or duration control for profiles default embeddings openai compat timeout. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__ALLOWED_SOURCES` | `["upload", "text", "filesystem", "s3", "webdav", "gdrive"]` | Optional | `<set as needed>` | Configuration value for profiles default ingestion allowed sources. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__FILESYSTEM__ROOTS` | `["${INGEST_ROOT:./uploads}"]` | Optional | `<set as needed>` | Configuration value for profiles default ingestion filesystem roots. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__FILESYSTEM__DENY_GLOBS` | `["**/.git/**", "**/node_modules/**"]` | Optional | `<set as needed>` | Configuration value for profiles default ingestion filesystem deny globs. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__MAX_FILE_MB` | `50` | Optional | `50` | Configuration value for profiles default ingestion max file mb. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__DEDUPE__MODE` | `hash` | Optional | `hash` | Configuration value for profiles default ingestion dedupe mode. |
| `CLOUD_DOG__PROFILES__DEFAULT__INGESTION__DEDUPE__POLICY` | `skip` | Optional | `skip` | Configuration value for profiles default ingestion dedupe policy. |
| `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__STRATEGY` | `token` | Optional | `token` | Configuration value for profiles default chunking strategy. |
| `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__CHUNK_SIZE` | `800` | Optional | `800` | Configuration value for profiles default chunking chunk size. |
| `CLOUD_DOG__PROFILES__DEFAULT__CHUNKING__CHUNK_OVERLAP` | `100` | Optional | `100` | Configuration value for profiles default chunking chunk overlap. |
| `CLOUD_DOG__PROFILES__DEFAULT__SEARCH__TOP_K_DEFAULT` | `10` | Optional | `10` | Configuration value for profiles default search top k default. |
| `CLOUD_DOG__PROFILES__DEFAULT__SEARCH__SCORE_THRESHOLD` | `0.0` | Optional | `0.0` | Configuration value for profiles default search score threshold. |

## `queue`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__QUEUE__BACKEND` | `${CLOUD_DOG__INDEX__QUEUE__BACKEND:sql}` | Optional | `${CLOUD_DOG__INDEX__QUEUE__BACKEND:sql}` | Configuration value for queue backend. |
| `CLOUD_DOG__QUEUE__DATABASE_URL` | `${INDEX_RETRIEVER_DB_URL:${DB_URL:sqlite+aiosqlite:///./data/...` | Deployment dependent | `${INDEX_RETRIEVER_DB_URL:${DB_URL:sqlite+aiosqlite:///./data/...` | Endpoint or connection URL for queue database. |
| `CLOUD_DOG__QUEUE__SERVER_ID` | `${INDEX_RETRIEVER_SERVER_ID:${HOSTNAME:index-retriever-local}}` | Optional | `${INDEX_RETRIEVER_SERVER_ID:${HOSTNAME:index-retriever-local}}` | Configuration value for queue server id. |
| `CLOUD_DOG__QUEUE__MAX_CONCURRENCY` | `8` | Optional | `8` | Configuration value for queue max concurrency. |
| `CLOUD_DOG__QUEUE__PER_PROFILE_CONCURRENCY` | `2` | Optional | `2` | Configuration value for queue per profile concurrency. |
| `CLOUD_DOG__QUEUE__DEFAULT_TIMEOUT_SECONDS` | `1800` | Optional | `1800` | Timeout or duration control for queue default timeout. |
| `CLOUD_DOG__QUEUE__RETRY__MAX_ATTEMPTS` | `3` | Optional | `3` | Configuration value for queue retry max attempts. |
| `CLOUD_DOG__QUEUE__RETRY__BACKOFF_SECONDS` | `5` | Optional | `5` | Timeout or duration control for queue retry backoff. |
| `CLOUD_DOG__QUEUE__REDIS__ENABLED` | `false` | Optional | `false` | Toggle for queue redis. |
| `CLOUD_DOG__QUEUE__REDIS__URL` | `${REDIS_URL:redis://127.0.0.1:6379/0}` | Deployment dependent | `https://service.example.com` | Endpoint or connection URL for queue redis. |

## `rbac`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__RBAC__ENABLED` | `true` | Optional | `true` | Toggle for rbac. |
| `CLOUD_DOG__RBAC__DEFAULT_DENY` | `true` | Optional | `true` | Configuration value for rbac default deny. |
| `CLOUD_DOG__RBAC__ROLES__ADMIN` | `["*"]` | Optional | `<set as needed>` | Configuration value for rbac roles admin. |
| `CLOUD_DOG__RBAC__ROLES__MAINTAINER` | `["profiles_*", "collections_*", "ingest_*", "search", "retrieve", "delete_*", "retention_*", "reindex_*", "job_*", "queu...` | Optional | `<set as needed>` | Configuration value for rbac roles maintainer. |
| `CLOUD_DOG__RBAC__ROLES__WRITER` | `["ingest_*", "search", "retrieve", "job_list", "job_get", "job_wait", "job_stream", "queue_status"]` | Optional | `<set as needed>` | Configuration value for rbac roles writer. |
| `CLOUD_DOG__RBAC__ROLES__READER` | `["profiles_list", "profile_get", "collections_list", "collection_get", "search", "retrieve", "search_explain", "job_get"...` | Optional | `<set as needed>` | Configuration value for rbac roles reader. |

## `storage`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__STORAGE__DB__URL` | `${DB_URL:sqlite+aiosqlite:///./data/index_retriever.db}` | Deployment dependent | `https://service.example.com` | Endpoint or connection URL for storage db. |
| `CLOUD_DOG__STORAGE__AUDIT__PATH` | `${AUDIT_LOG_PATH:./logs/audit.log}` | Optional | `./data/service.dat` | Configuration value for storage audit path. |

## `web_server`

| Variable | Default | Required | Example | Description |
|----------|---------|----------|---------|-------------|
| `CLOUD_DOG__WEB_SERVER__HOST` | `0.0.0.0` | Optional | `0.0.0.0` | Host binding or upstream host for web server. |
| `CLOUD_DOG__WEB_SERVER__PORT` | `8075` | Optional | `8075` | Port for web server connections. |

## Vault Support

| Variable | Purpose | Example |
|----------|---------|---------|
| `VAULT_ADDR` | Vault server URL when using secret-backed config resolution. | `https://your-vault-server` |
| `VAULT_TOKEN` | Token-based authentication for Vault when applicable. | `your-vault-token` |
| `VAULT_MOUNT_POINT` | Secret mount used by your Vault deployment. | `secret` |
| `VAULT_CONFIG_PATH` | Config path holding service settings. | `services/your-service` |
