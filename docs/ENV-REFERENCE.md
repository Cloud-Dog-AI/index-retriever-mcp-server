# Environment Reference — index-retriever-mcp-server

## 1. Configuration Precedence

`os.environ → .env → config.yaml → defaults.yaml → Vault`

Runtime loading uses `cloud_dog_config` through `src/index_tools/config/loader.py` with strict unresolved-variable handling.

## 2. Variables by Category

Columns: `Variable`, `Description`, `Default`, `Required`, `Example`

### Auth & Secrets

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `API_KEY` | Configuration for api key. | `-` | No | `***` |
| `CHROMA_AUTH_TOKEN` | Configuration for chroma auth token. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__API_KEY` | Configuration for cloud dog index api key. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__AUTH__API_KEYS` | Comma-separated API keys accepted by auth middleware. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__EMBEDDING__API_KEY` | Configuration for cloud dog index embedding api key. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__VDB__API_KEY` | Configuration for cloud dog index vdb api key. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__VDB__CHROMA_AUTH_TOKEN` | Configuration for cloud dog index vdb chroma auth token. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__VDB__INFINITY_API_KEY` | Configuration for cloud dog index vdb infinity api key. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__VDB__QDRANT_API_KEY` | Configuration for cloud dog index vdb qdrant api key. | `-` | No | `***` |
| `CLOUD_DOG__INDEX__VDB__WEAVIATE_API_KEY` | Configuration for cloud dog index vdb weaviate api key. | `-` | No | `***` |
| `EMBED_API_KEY` | Configuration for embed api key. | `-` | No | `***` |
| `INDEX_MCP_AUTH_MODE` | Configuration for index mcp auth mode. | `-` | No | `<set-in-env>` |
| `INFINITY_API_KEY` | Configuration for infinity api key. | `-` | No | `***` |
| `MARKER_MCP_AUTH_TOKEN` | Configuration for marker mcp auth token. | `-` | No | `***` |
| `MINERU_API_KEY` | Configuration for mineru api key. | `-` | No | `***` |
| `QDRANT_API_KEY` | Configuration for qdrant api key. | `-` | No | `***` |
| `TEST_A2A_API_KEY` | Expected API key used by A2A auth contract tests. | `-` | No | `***` |
| `WEAVIATE_API_KEY` | Configuration for weaviate api key. | `-` | No | `***` |

### Core & Misc

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `AUDIT_LOG_PATH` | Configuration for audit log path. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_ENV_FILES` | Optional env file list consumed by runtime bootstrap wrappers. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__API_AUDIT_PATH` | API audit log output path override. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__AUDIT__ENABLED` | Configuration for cloud dog index audit enabled. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__LLM__BASE_URL` | Configuration for cloud dog index llm base url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__LLM__MODEL` | Configuration for cloud dog index llm model. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__LLM__PROVIDER` | Configuration for cloud dog index llm provider. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__LOG__LEVEL` | Configuration for cloud dog index log level. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__MCP_AUDIT_PATH` | MCP audit log output path override. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__STORAGE__AUDIT__PATH` | Fallback audit log path used by API/MCP services. | `-` | No | `<set-in-env>` |
| `DRY_RUN` | Configuration for dry run. | `true` | No | `<set-in-env>` |
| `ENV_FILE` | Configuration for env file. | `-` | No | `<set-in-env>` |
| `INGEST_ROOT` | Configuration for ingest root. | `-` | No | `<set-in-env>` |
| `JWT_AUDIENCE` | Configuration for jwt audience. | `-` | No | `<set-in-env>` |
| `JWT_ISSUER` | Configuration for jwt issuer. | `-` | No | `<set-in-env>` |
| `JWT_JWKS_URL` | Configuration for jwt jwks url. | `-` | No | `https://example.internal` |
| `NO_PROXY` | Configuration for no proxy. | `-` | No | `<set-in-env>` |
| `REQUIRE_ALL_PDF_PARSERS` | Configuration for require all pdf parsers. | `-` | No | `<set-in-env>` |

### Database

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CLOUD_DOG_DB__DATABASE` | Configuration for cloud dog db database. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_DB__DIALECT` | Configuration for cloud dog db dialect. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_DB__HOST` | Configuration for cloud dog db host. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_DB__PASSWORD` | Configuration for cloud dog db password. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_DB__PORT` | Configuration for cloud dog db port. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG_DB__USERNAME` | Configuration for cloud dog db username. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__DB__DATABASE` | Configuration for cloud dog db database. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__DB__DIALECT` | Configuration for cloud dog db dialect. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__DB__URL` | Configuration for cloud dog index db url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__CHROMA_URL` | Configuration for cloud dog index vdb chroma url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__COLLECTION` | Configuration for cloud dog index vdb collection. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__HOST` | Configuration for cloud dog index vdb host. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__INFINITY_HOST` | Configuration for cloud dog index vdb infinity host. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__INFINITY_PORT` | Configuration for cloud dog index vdb infinity port. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__INFINITY_URL` | Configuration for cloud dog index vdb infinity url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_BASE_URL` | Configuration for cloud dog index vdb opensearch base url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_HOST` | Configuration for cloud dog index vdb opensearch host. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_PASSWORD` | Configuration for cloud dog index vdb opensearch password. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_PORT` | Configuration for cloud dog index vdb opensearch port. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_URL` | Configuration for cloud dog index vdb opensearch url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__OPENSEARCH_USERNAME` | Configuration for cloud dog index vdb opensearch username. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__PGVECTOR_DATABASE_URI` | Configuration for cloud dog index vdb pgvector database uri. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__PGVECTOR_URL` | Configuration for cloud dog index vdb pgvector url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__PORT` | Configuration for cloud dog index vdb port. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__PROVIDER` | Configuration for cloud dog index vdb provider. | `-` | Yes | `<set-in-env>` |
| `CLOUD_DOG__INDEX__VDB__QDRANT_URL` | Configuration for cloud dog index vdb qdrant url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__VDB__WEAVIATE_URL` | Configuration for cloud dog index vdb weaviate url. | `-` | No | `https://example.internal` |
| `DB_URL` | Configuration for db url. | `-` | No | `https://example.internal` |
| `INDEX_RETRIEVER_DB_URL` | Configuration for index retriever db url. | `-` | No | `https://example.internal` |
| `PGVECTOR_DATABASE_URI` | Configuration for pgvector database uri. | `-` | No | `<set-in-env>` |

### Embedding & Parser Services

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CLOUD_DOG__INDEX__EMBEDDING__BASE_URL` | Configuration for cloud dog index embedding base url. | `-` | No | `https://example.internal` |
| `CLOUD_DOG__INDEX__EMBEDDING__DIMENSIONS` | Configuration for cloud dog index embedding dimensions. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__EMBEDDING__MODEL` | Configuration for cloud dog index embedding model. | `-` | Yes | `<set-in-env>` |
| `CLOUD_DOG__INDEX__EMBEDDING__PROVIDER` | Configuration for cloud dog index embedding provider. | `-` | Yes | `<set-in-env>` |
| `DEEPDOC_COMMAND` | Configuration for deepdoc command. | `-` | No | `<set-in-env>` |
| `DEEPDOC_ENABLED` | Configuration for deepdoc enabled. | `-` | No | `<set-in-env>` |
| `DEEPDOC_TIMEOUT_SECONDS` | Configuration for deepdoc timeout seconds. | `-` | No | `<set-in-env>` |
| `DOCLING_COMMAND` | Configuration for docling command. | `-` | No | `<set-in-env>` |
| `DOCLING_ENABLED` | Configuration for docling enabled. | `-` | No | `<set-in-env>` |
| `DOCLING_TIMEOUT_SECONDS` | Configuration for docling timeout seconds. | `-` | No | `<set-in-env>` |
| `EMBED_BASE_URL` | Configuration for embed base url. | `-` | No | `https://example.internal` |
| `EMBED_MODEL` | Configuration for embed model. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_ASYNC_MAX_WAIT_SECONDS` | Configuration for marker mcp async max wait seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_ASYNC_POLL_INTERVAL_SECONDS` | Configuration for marker mcp async poll interval seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_ASYNC_THRESHOLD_SECONDS` | Configuration for marker mcp async threshold seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_BASE_URL` | Configuration for marker mcp base url. | `-` | No | `https://example.internal` |
| `MARKER_MCP_BUSY_RETRY_BACKOFF` | Configuration for marker mcp busy retry backoff. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_BUSY_RETRY_INITIAL_SECONDS` | Configuration for marker mcp busy retry initial seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_BUSY_RETRY_MAX_DELAY_SECONDS` | Configuration for marker mcp busy retry max delay seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_BUSY_RETRY_MAX_SECONDS` | Configuration for marker mcp busy retry max seconds. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_DOC_TIMEOUT_SECONDS` | Configuration for marker mcp doc timeout seconds. | `1200` | No | `<set-in-env>` |
| `MARKER_MCP_ENABLED` | Configuration for marker mcp enabled. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_REQUEST_RETRIES` | Configuration for marker mcp request retries. | `-` | No | `<set-in-env>` |
| `MARKER_MCP_TIMEOUT_SECONDS` | Configuration for marker mcp timeout seconds. | `1200` | No | `<set-in-env>` |
| `MINERU_BASE_URL` | Configuration for mineru base url. | `-` | No | `https://example.internal` |
| `MINERU_DOC_TIMEOUT_SECONDS` | Configuration for mineru doc timeout seconds. | `240` | No | `<set-in-env>` |
| `MINERU_ENABLED` | Configuration for mineru enabled. | `-` | No | `<set-in-env>` |
| `MINERU_FORMULA_ENABLE` | Configuration for mineru formula enable. | `-` | No | `<set-in-env>` |
| `MINERU_PAGE_FALLBACK_MAX_PAGES` | Configuration for mineru page fallback max pages. | `-` | No | `<set-in-env>` |
| `MINERU_PAGE_FALLBACK_TARGET_CHARS` | Configuration for mineru page fallback target chars. | `-` | No | `<set-in-env>` |
| `MINERU_PARSE_BACKEND` | Configuration for mineru parse backend. | `-` | No | `<set-in-env>` |
| `MINERU_PARSE_METHOD` | Configuration for mineru parse method. | `-` | No | `<set-in-env>` |
| `MINERU_REQUEST_RETRIES` | Configuration for mineru request retries. | `-` | No | `<set-in-env>` |
| `MINERU_RETURN_IMAGES` | Configuration for mineru return images. | `-` | No | `<set-in-env>` |
| `MINERU_RETURN_MIDDLE_JSON` | Configuration for mineru return middle json. | `-` | No | `<set-in-env>` |
| `MINERU_TABLE_ENABLE` | Configuration for mineru table enable. | `-` | No | `<set-in-env>` |
| `MINERU_TIMEOUT_SECONDS` | Configuration for mineru timeout seconds. | `180` | No | `<set-in-env>` |
| `PARSER_PROVIDER_TIMEOUT_SECONDS` | Configuration for parser provider timeout seconds. | `240` | No | `<set-in-env>` |
| `TRANSFORMERS_BASE_URL` | Configuration for transformers base url. | `-` | No | `https://example.internal` |
| `TRANSFORMERS_COMMAND` | Configuration for transformers command. | `-` | No | `<set-in-env>` |
| `TRANSFORMERS_ENABLED` | Configuration for transformers enabled. | `-` | No | `<set-in-env>` |
| `TRANSFORMERS_TIMEOUT_SECONDS` | Configuration for transformers timeout seconds. | `180` | No | `<set-in-env>` |

### Server Runtime

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CLOUD_DOG__INDEX__API_SERVER__HOST` | Configuration for cloud dog index api server host. | `0.0.0.0` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__API_SERVER__PORT` | Configuration for cloud dog index api server port. | `8686` | No | `8686` |
| `CLOUD_DOG__INDEX__MCP_SERVER__HOST` | Configuration for cloud dog index mcp server host. | `0.0.0.0` | No | `<set-in-env>` |
| `CLOUD_DOG__INDEX__MCP_SERVER__PORT` | Configuration for cloud dog index mcp server port. | `8687` | No | `8686` |
| `INDEX_MCP_HOST` | Configuration for index mcp host. | `-` | No | `<set-in-env>` |
| `INDEX_MCP_MCP_ENABLED` | Configuration for index mcp mcp enabled. | `-` | No | `<set-in-env>` |
| `INDEX_MCP_MCP_PORT` | Configuration for index mcp mcp port. | `-` | No | `<set-in-env>` |
| `INDEX_MCP_PORT` | Configuration for index mcp port. | `-` | No | `<set-in-env>` |

### Test & Runtime Harness

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `INDEX_RETRIEVER_API_BASE_URL` | Configuration for index retriever api base url. | `-` | No | `https://example.internal` |
| `INDEX_RETRIEVER_CHROMA_PURGE_REGEX` | Configuration for index retriever chroma purge regex. | `-` | No | `<set-in-env>` |
| `INDEX_RETRIEVER_DEFAULT_BACKEND` | Configuration for index retriever default backend. | `-` | No | `<set-in-env>` |
| `INDEX_RETRIEVER_LIVE_REQUIRED_PROVIDERS` | Configuration for index retriever live required providers. | `chroma` | No | `<set-in-env>` |
| `INDEX_RETRIEVER_LIVE_USE_VAULT_FALLBACK` | Configuration for index retriever live use vault fallback. | `-` | No | `<set-in-env>` |
| `INDEX_RETRIEVER_MCP_BASE_URL` | Configuration for index retriever mcp base url. | `-` | No | `https://example.internal` |
| `INDEX_RETRIEVER_RUNTIME_MODE` | Configuration for index retriever runtime mode. | `local-server` | No | `<set-in-env>` |
| `INDEX_RETRIEVER_TEST_RUN_PREFIX` | Run prefix used to isolate test-created resources. | `-` | No | `<set-in-env>` |
| `LOCAL_DOCKER_COMPOSE_FILE` | Configuration for local docker compose file. | `-` | No | `<set-in-env>` |
| `LOCAL_DOCKER_COMPOSE_PROFILES` | Configuration for local docker compose profiles. | `-` | No | `<set-in-env>` |
| `LOCAL_DOCKER_PROJECT_NAME` | Configuration for local docker project name. | `-` | No | `<set-in-env>` |
| `LOCAL_DOCKER_SERVICES` | Configuration for local docker services. | `-` | No | `<set-in-env>` |
| `LOCAL_DOCKER_SOURCE_ENV` | Configuration for local docker source env. | `-` | No | `<set-in-env>` |
| `PYTEST_CURRENT_TEST` | Pytest internal marker used to adjust middleware in tests. | `-` | No | `<set-in-env>` |
| `TEST_A2A_BASE_PATH` | Configuration for test a2a base path. | `/a2a` | No | `tests/env-<TIER>` |
| `TEST_API_BASE_PATH` | Configuration for test api base path. | `/app/v1` | No | `tests/env-<TIER>` |
| `TEST_ENV_TIER` | Configuration for test env tier. | `-` | No | `tests/env-<TIER>` |
| `TEST_MCP_BASE_PATH` | Configuration for test mcp base path. | `/mcp` | No | `tests/env-<TIER>` |
| `TEST_WEB_BASE_PATH` | Configuration for test web base path. | `/` | No | `tests/env-<TIER>` |

### Vault

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CLOUD_DOG__VAULT__ADDR` | Configuration for cloud dog vault addr. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__VAULT__CONFIG_PATH` | Configuration for cloud dog vault config path. | `-` | No | `<set-in-env>` |
| `CLOUD_DOG__VAULT__MOUNT_POINT` | Configuration for cloud dog vault mount point. | `-` | No | `<set-in-env>` |
| `VAULT_ADDR` | Vault server base URL. | `-` | No | `https://vault.cloud-dog.net` |
| `VAULT_CONFIG_PATH` | Vault config JSON path. | `-` | No | `<set-in-env>` |
| `VAULT_MOUNT_POINT` | Vault KV mount point. | `-` | No | `<set-in-env>` |
| `VAULT_TOKEN` | Vault access token for runtime secret resolution. | `-` | No | `***` |

### Vector Backends

| Variable | Description | Default | Required | Example |
|---|---|---|---|---|
| `CHROMA_PATH` | Configuration for chroma path. | `-` | No | `<set-in-env>` |
| `CHROMA_URL` | Configuration for chroma url. | `-` | No | `https://example.internal` |
| `INFINITY_HOST` | Configuration for infinity host. | `-` | No | `<set-in-env>` |
| `INFINITY_PORT` | Configuration for infinity port. | `-` | No | `<set-in-env>` |
| `INFINITY_URL` | Configuration for infinity url. | `-` | No | `https://example.internal` |
| `OPENSEARCH_HOST` | Configuration for opensearch host. | `-` | No | `<set-in-env>` |
| `OPENSEARCH_PASSWORD` | Configuration for opensearch password. | `-` | No | `<set-in-env>` |
| `OPENSEARCH_PORT` | Configuration for opensearch port. | `-` | No | `<set-in-env>` |
| `OPENSEARCH_URL` | Configuration for opensearch url. | `-` | No | `https://example.internal` |
| `OPENSEARCH_USERNAME` | Configuration for opensearch username. | `-` | No | `<set-in-env>` |
| `QDRANT_HOST` | Configuration for qdrant host. | `-` | No | `<set-in-env>` |
| `QDRANT_PORT` | Configuration for qdrant port. | `-` | No | `<set-in-env>` |
| `QDRANT_URL` | Configuration for qdrant url. | `-` | No | `https://example.internal` |
| `WEAVIATE_URL` | Configuration for weaviate url. | `-` | No | `https://example.internal` |

## 3. Vault Integration

Load Vault bootstrap before IT/AT or any runtime requiring secrets:

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
bash scripts/validate-vault.sh
```

Vault sections used by this project:
- `dev.databases`
- `dev.models`
- `dev.vdbs`
- `dev.storage`
- `dev.redis`
- `dev.repository`

## 4. Example Configurations

### Local Development (SQLite, minimal auth)

```bash
DB_URL=sqlite+aiosqlite:///./data/index_retriever.db
CLOUD_DOG__INDEX__VDB__PROVIDER=chroma
CLOUD_DOG__INDEX__EMBEDDING__PROVIDER=openai_compat
CLOUD_DOG__INDEX__EMBEDDING__MODEL=nomic-embed-text
```

### Docker/Preprod (PostgreSQL + Vault)

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
CLOUD_DOG__INDEX__DB__URL=${vault.dev.databases.index_retriever.url}
CLOUD_DOG__INDEX__VDB__QDRANT_URL=${vault.dev.vdbs.qdrant.url}
CLOUD_DOG__INDEX__EMBEDDING__BASE_URL=${vault.dev.models.ollama.base_url}
```

### Production

Use Vault-backed values for all credential-bearing keys (`*_API_KEY`, `*_TOKEN`, DB passwords) and lock down API keys to managed IDAM flows.

