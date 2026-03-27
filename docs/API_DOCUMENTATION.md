# API Documentation

## Base URLs

| Surface | Default Port | Local URL |
|---------|-------------|-----------|
| API Server | 8074 | `http://localhost:8074` |
| Web Server | 8075 | `http://localhost:8075` |
| MCP Server | 8076 | `http://localhost:8076` |
| A2A Server | 8077 | `http://localhost:8077` |

Deployed: `https://index-retriever.your-domain.com`

## Authentication

- **Cookie session:** `POST /auth/login` with `{"username": "...", "password": "..."}`
- **API Key:** `X-API-Key: <your-api-key>` or `Authorization: Bearer <your-api-key>`
- **JWT:** `Authorization: Bearer <jwt-token>` (when jwt or apikey+jwt mode is configured)

## Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | No | Service health check (db, vdb, embedding) |
| GET | /ready | No | Readiness probe |
| GET | /live | No | Liveness probe |
| GET | /status | No | Extended status |
| GET | /app/v1/health | API Key | API-scoped health check |
| GET | /a2a/health | API Key | A2A-scoped health check |

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /auth/login | No | Login with username/password |
| GET | /auth/me | Session | Current authenticated user |
| POST | /auth/logout | Session | Destroy session |

### Tools

Available at both `/app/v1` (canonical) and `/api/v1` (legacy) base paths.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /app/v1/tools | API Key | List available tools |
| POST | /app/v1/tools/{tool_name} | API Key | Call a tool |
| GET | /app/v1/tools/{tool_name} | API Key | Call a read-only status tool (GET alias) |

### MCP Tools (via MCP protocol or REST)

| Tool | Description |
|------|-------------|
| search | Semantic search across indexed documents |
| retrieve | Retrieve specific documents by ID |
| search_explain | Search with scoring explanation |
| ingest_text | Ingest text content |
| ingest_file | Ingest a file |
| ingest_url | Ingest from URL |
| delete_document | Delete a document |
| delete_collection | Delete a collection |
| profiles_list | List profiles |
| profile_get | Get profile details |
| collections_list | List collections |
| collection_get | Get collection details |
| retention_apply | Apply retention policies |
| reindex_collection | Reindex a collection |
| backend_health_check | VDB backend health |
| embedding_health_check | Embedding service health |
| job_list | List jobs |
| job_get | Get job status |
| job_wait | Wait for job completion |
| job_stream | Stream job progress |
| queue_status | Job queue status |

### File Upload

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /app/v1/upload | API Key | Upload and ingest a file (multipart) |

### Admin Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/profiles | API Key | List all profiles |
| POST | /admin/profiles | API Key | Create a profile |
| GET | /admin/profiles/{profile_id} | API Key | Get a profile |
| PUT | /admin/profiles/{profile_id} | API Key | Update a profile |
| DELETE | /admin/profiles/{profile_id} | API Key | Delete a profile |

### Admin Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/users | API Key | List all users |
| POST | /admin/users | API Key | Create a user |
| GET | /admin/users/{user_id} | API Key | Get a user |
| PUT | /admin/users/{user_id} | API Key | Update a user |
| DELETE | /admin/users/{user_id} | API Key | Delete a user |

### Admin Groups

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/groups | API Key | List all groups |
| POST | /admin/groups | API Key | Create a group |
| GET | /admin/groups/{group_id} | API Key | Get a group |
| PUT | /admin/groups/{group_id} | API Key | Update a group |
| DELETE | /admin/groups/{group_id} | API Key | Delete a group |

### Admin API Keys

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/api-keys | API Key | List all API keys |
| POST | /admin/api-keys | API Key | Create an API key |
| DELETE | /admin/api-keys/{key_id} | API Key | Delete an API key |

### Admin Collections

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/collections | API Key | List all collections |
| POST | /admin/collections | API Key | Create a collection |
| GET | /admin/collections/{collection_id} | API Key | Get a collection |
| PUT | /admin/collections/{collection_id} | API Key | Update a collection |
| DELETE | /admin/collections/{collection_id} | API Key | Delete a collection |

### Admin Source Configs

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/source-configs | API Key | List source configurations |
| POST | /admin/source-configs | API Key | Create a source config |
| GET | /admin/source-configs/{source_id} | API Key | Get a source config |
| PUT | /admin/source-configs/{source_id} | API Key | Update a source config |
| DELETE | /admin/source-configs/{source_id} | API Key | Delete a source config |

### Admin RBAC

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/rbac-bindings | API Key | List RBAC bindings |
| POST | /admin/rbac-bindings | API Key | Create an RBAC binding |
| DELETE | /admin/rbac-bindings/{entity_type}/{entity_id}/{role} | API Key | Delete an RBAC binding |

### A2A

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /a2a | API Key | A2A root info |
| GET | /a2a/health | API Key | A2A health check |
| GET | /a2a/events | API Key | A2A configuration events |

### Admin UI

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /admin/ui | Session | Admin UI root |
| GET | /admin/ui/profiles | Session | Profile management page |
| GET | /admin/ui/security | Session | Security management page |
