# MCP Server Documentation — Index Retriever MCP Server

## Transport
Streamable HTTP at `/mcp`

Tool endpoints at `/mcp/tools`.

## Authentication
Include API key: `Authorization: Bearer <your-api-key>` or `X-API-Key: <your-api-key>`

Roles: `reader`, `writer`, `maintainer`, `admin`. Admin tools require `admin` role.

## Tools

### Profile & Identity Management

#### profiles_list
**Description:** List configured profiles.

*No parameters required.* Roles: reader, writer, maintainer, admin.

#### profile_get
**Description:** Get a single profile by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |

#### admin_profile_create
**Description:** Create a profile configuration. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| config | object | No | Profile configuration |

#### admin_profile_update
**Description:** Update a profile configuration. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| config | object | No | Configuration updates |

#### admin_profile_delete
**Description:** Delete a profile. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |

#### users_list
**Description:** List configured users.

*No parameters required.*

#### user_get
**Description:** Get a single user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID |

#### admin_user_create / admin_user_update / admin_user_delete
**Description:** CRUD operations for users. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID |

#### groups_list / group_get / admin_group_create / admin_group_update / admin_group_delete
**Description:** CRUD operations for groups. Admin operations require admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| group_id | string | Yes | Group ID |

#### api_keys_list / admin_api_key_create / admin_api_key_revoke
**Description:** API key management. Admin operations require admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| key_id | string | Yes (revoke) | API key ID |

### Collection Management

#### collections_list
**Description:** List collections for a profile.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | No | Profile name (default: "default") |

#### collection_get
**Description:** Get collection details.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | No | Profile name |
| collection | string | Yes | Collection name |

#### admin_collection_create / admin_collection_update / admin_collection_delete
**Description:** CRUD for collections. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | No | Profile name |
| collection | string | Yes | Collection name |

### Source Configuration

#### source_configs_list / source_config_get
**Description:** List or get source configurations.

#### admin_source_config_create / admin_source_config_update / admin_source_config_delete
**Description:** CRUD for source configurations. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| source_id | string | Yes | Source config ID |

### RBAC

#### rbac_bindings_list
**Description:** List RBAC bindings. Requires admin role.

#### admin_rbac_bind / admin_rbac_unbind
**Description:** Bind or unbind an RBAC role. Requires admin role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| entity_type | string | Yes | Entity type |
| entity_id | string | Yes | Entity ID |
| role | string | Yes | Role name |

### A2A Events

#### a2a_config_events
**Description:** List agent-to-agent configuration change events.

*No parameters required.*

### Ingestion

#### ingest_upload
**Description:** Ingest a file by uploading content. Requires writer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| filename | string | Yes | Original filename |
| content | string | Yes | File content (text or base64) |
| metadata | object | No | Document metadata |

#### ingest_text
**Description:** Ingest inline text content. Requires writer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| text | string | Yes | Text content |
| source | string | No | Source identifier |

#### ingest_reference
**Description:** Ingest content by reference. Requires writer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| reference | string | Yes | Reference URI |

#### ingest_stream_open / ingest_stream_event / ingest_stream_close
**Description:** Streaming ingestion lifecycle. Requires writer role.

#### ingest_preview
**Description:** Preview ingestion parsing result without persisting.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Input text |
| source_uri | string | No | Source URI |
| parser_chain | array | No | Parser chain |
| ocr_mode | string | No | OCR mode |
| table_policy | string | No | Table handling policy |

#### extract_only
**Description:** Extract content without indexing. Requires writer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Input text |
| source_uri | string | No | Source URI |
| parser_chain | array | No | Parser chain |

### Parsing

#### parsers_list
**Description:** List available parser providers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| parser_services | object | No | Parser services configuration |

#### parser_test
**Description:** Test a parser with sample input. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| provider_id | string | Yes | Parser provider ID |
| sample_text | string | No | Sample text |

### OCR & Tables

#### ocr_run
**Description:** Run OCR on text. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Input text |
| mode | string | No | OCR mode (auto, force) |
| provider_id | string | No | OCR provider |

#### table_extract
**Description:** Extract tables from content. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Input text |
| table_policy | string | No | Policy (table_as_markdown, table_as_json) |

### Search & Retrieval

#### search
**Description:** Search indexed content by query.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| query | string | Yes | Search query |
| top_k | integer | No | Number of results (default: 10) |
| filters | object | No | Structured filters |

#### retrieve
**Description:** Retrieve a document by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| document_id | string | Yes | Document ID |

#### search_explain
**Description:** Search with scoring explanation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| query | string | Yes | Search query |
| top_k | integer | No | Number of results |

### Job Management

#### job_list
**Description:** List indexing jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status |
| limit | integer | No | Maximum results (default: 50) |

#### job_get
**Description:** Get job details.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID |

#### job_wait
**Description:** Wait for a job to complete.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID |

#### job_cancel
**Description:** Cancel a running job.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID |

#### job_retry
**Description:** Retry a failed job.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID |

#### job_stream
**Description:** Stream job progress events.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID |

#### queue_status
**Description:** Get queue health and depth.

*No parameters required.*

### Deletion & Maintenance

#### delete_by_id
**Description:** Delete a document by ID. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| document_id | string | Yes | Document ID |

#### delete_by_filter
**Description:** Delete documents matching a filter. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |
| filter | object | Yes | Filter criteria |

#### retention_run
**Description:** Execute retention policy. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |

#### reindex_run
**Description:** Trigger a full reindex. Requires maintainer role.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| profile | string | Yes | Profile name |
| collection | string | Yes | Collection name |

### Health Checks

#### backend_health_check
**Description:** Check vector database backend health.

*No parameters required.*

#### embedding_health_check
**Description:** Check embedding service health.

*No parameters required.*
