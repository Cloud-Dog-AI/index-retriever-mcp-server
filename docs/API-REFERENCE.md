# API Reference — index-retriever-mcp-server

## REST API

### Authentication

- `X-API-Key: <key>` or `Authorization: Bearer <key>`
- A2A endpoints require API-key auth and return `401` when missing/invalid.

### Endpoints

| Method | Path | Description | Auth | Request | Response | Errors |
|---|---|---|---|---|---|---|
| GET | `/health` | Service health probe | No | None | `{"status":"ok"}` + checks | `500` |
| GET | `/app/v1/health` | Canonical API health | No | None | `{"status":"ok"}` + checks | `500` |
| GET | `/app/v1/tools` | List tool catalogue | Yes | None | Tool schema array | `401`,`403` |
| POST | `/app/v1/tools/{tool_name}` | Execute tool | Yes | JSON payload | Tool-specific JSON | `400`,`401`,`403`,`404` |
| GET | `/api/v1/tools` | Legacy alias tool list | Yes | None | Tool schema array | `401`,`403` |
| POST | `/api/v1/tools/{tool_name}` | Legacy alias tool call | Yes | JSON payload | Tool-specific JSON | `400`,`401`,`403`,`404` |

## MCP Tools

MCP tool schemas are exposed by `GET /mcp/tools` (and legacy alias where enabled).

### `profiles_list`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "profiles_list"
}
```

### `profile_get`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "profile_get"
}
```

### `admin_profile_create`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "admin_profile_create"
}
```

### `admin_profile_update`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "admin_profile_update"
}
```

### `admin_profile_delete`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "admin_profile_delete"
}
```

### `collections_list`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "collections_list"
}
```

### `collection_get`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "collection_get"
}
```

### `admin_collection_create`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "admin_collection_create"
}
```

### `admin_collection_delete`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "admin_collection_delete"
}
```

### `ingest_upload`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `job_id` | `string` | Yes |  |
| `status` | `string` | Yes |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "ingest_upload"
}
```

### `ingest_text`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | Yes |  |
| `collection` | `string` | Yes |  |
| `text` | `string` | Yes |  |
| `source` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `job_id` | `string` | Yes |  |
| `status` | `string` | Yes |  |

**Example**

```json
{
  "payload": {
    "collection": "<collection>",
    "profile": "<profile>",
    "text": "<text>"
  },
  "tool_name": "ingest_text"
}
```

### `ingest_reference`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `job_id` | `string` | Yes |  |
| `status` | `string` | Yes |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "ingest_reference"
}
```

### `parsers_list`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `parser_services` | `object` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `parsers` | `array` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "parsers_list"
}
```

### `parser_test`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `provider_id` | `string` | Yes |  |
| `sample_text` | `string` | No |  |
| `source_uri` | `string` | No |  |
| `parser_services` | `object` | No |  |
| `options` | `object` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `provider_id` | `string` | Yes |  |
| `provider_version` | `string` | Yes |  |
| `healthy` | `boolean` | Yes |  |
| `text_blocks` | `integer` | Yes |  |
| `table_blocks` | `integer` | Yes |  |
| `quality` | `object` | No |  |

**Example**

```json
{
  "payload": {
    "provider_id": "<provider_id>"
  },
  "tool_name": "parser_test"
}
```

### `ingest_preview`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `text` | `string` | Yes |  |
| `source_uri` | `string` | No |  |
| `parser_chain` | `array` | No |  |
| `parser_options` | `object` | No |  |
| `parser_services` | `object` | No |  |
| `metadata` | `object` | No |  |
| `ocr_mode` | `string` | No |  |
| `ocr_provider` | `string` | No |  |
| `table_policy` | `string` | No |  |
| `table_json_shape` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `source_uri` | `string` | Yes |  |
| `filename` | `string` | Yes |  |
| `mime_type` | `string` | Yes |  |
| `chunk_count` | `integer` | Yes |  |
| `parser_provider` | `string` | No |  |
| `parser_version` | `string` | No |  |
| `ocr_mode` | `string` | No |  |
| `ocr_applied` | `boolean` | No |  |
| `table_policy` | `string` | No |  |
| `checkpoints` | `array` | No |  |

**Example**

```json
{
  "payload": {
    "text": "<text>"
  },
  "tool_name": "ingest_preview"
}
```

### `extract_only`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `text` | `string` | Yes |  |
| `source_uri` | `string` | No |  |
| `parser_chain` | `array` | No |  |
| `parser_options` | `object` | No |  |
| `parser_services` | `object` | No |  |
| `metadata` | `object` | No |  |
| `ocr_mode` | `string` | No |  |
| `ocr_provider` | `string` | No |  |
| `table_policy` | `string` | No |  |
| `table_json_shape` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `source_uri` | `string` | Yes |  |
| `text` | `string` | Yes |  |
| `chunk_count` | `integer` | Yes |  |
| `parser_provider` | `string` | No |  |
| `ocr_applied` | `boolean` | No |  |
| `table_policy` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "text": "<text>"
  },
  "tool_name": "extract_only"
}
```

### `ocr_run`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `text` | `string` | Yes |  |
| `mode` | `string` | No |  |
| `provider_id` | `string` | No |  |
| `min_chars` | `integer` | No |  |
| `min_scanned_ratio` | `number` | No |  |
| `scanned_ratio` | `number` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `enabled` | `boolean` | Yes |  |
| `mode` | `string` | Yes |  |
| `reason` | `string` | Yes |  |
| `provider_id` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "text": "<text>"
  },
  "tool_name": "ocr_run"
}
```

### `table_extract`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `text` | `string` | Yes |  |
| `source_uri` | `string` | No |  |
| `parser_chain` | `array` | No |  |
| `parser_options` | `object` | No |  |
| `parser_services` | `object` | No |  |
| `metadata` | `object` | No |  |
| `ocr_mode` | `string` | No |  |
| `ocr_provider` | `string` | No |  |
| `table_policy` | `string` | No |  |
| `table_json_shape` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `source_uri` | `string` | Yes |  |
| `table_policy` | `string` | Yes |  |
| `table_json_shape` | `string` | Yes |  |
| `table_count` | `integer` | Yes |  |
| `tables` | `array` | No |  |
| `parser_provider` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "text": "<text>"
  },
  "tool_name": "table_extract"
}
```

### `ingest_stream_open`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "ingest_stream_open"
}
```

### `ingest_stream_event`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `job_id` | `string` | Yes |  |
| `status` | `string` | Yes |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "ingest_stream_event"
}
```

### `ingest_stream_close`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "ingest_stream_close"
}
```

### `search`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | Yes |  |
| `collection` | `string` | Yes |  |
| `query` | `string` | Yes |  |
| `top_k` | `integer` | No |  |
| `filters` | `object` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `results` | `array` | No |  |

**Example**

```json
{
  "payload": {
    "collection": "<collection>",
    "profile": "<profile>",
    "query": "<query>"
  },
  "tool_name": "search"
}
```

### `retrieve`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "retrieve"
}
```

### `search_explain`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | Yes |  |
| `collection` | `string` | Yes |  |
| `query` | `string` | Yes |  |
| `top_k` | `integer` | No |  |
| `filters` | `object` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `results` | `array` | No |  |

**Example**

```json
{
  "payload": {
    "collection": "<collection>",
    "profile": "<profile>",
    "query": "<query>"
  },
  "tool_name": "search_explain"
}
```

### `job_list`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_list"
}
```

### `job_get`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_get"
}
```

### `job_wait`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_wait"
}
```

### `job_stream`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_stream"
}
```

### `job_cancel`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_cancel"
}
```

### `job_retry`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "job_retry"
}
```

### `queue_status`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "queue_status"
}
```

### `delete_by_id`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "delete_by_id"
}
```

### `delete_by_filter`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "delete_by_filter"
}
```

### `retention_run`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "retention_run"
}
```

### `reindex_run`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "reindex_run"
}
```

### `backend_health_check`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "backend_health_check"
}
```

### `embedding_health_check`

**Parameters**

| Name | Type | Required | Notes |
|---|---|---|---|
| `profile` | `string` | No |  |
| `collection` | `string` | No |  |

**Return Schema**

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | `string` | No |  |

**Example**

```json
{
  "payload": {
    "profile": "default"
  },
  "tool_name": "embedding_health_check"
}
```

## A2A Endpoints

| Method | Path | Description | Auth | Response | Errors |
|---|---|---|---|---|---|
| GET | `/a2a` | A2A namespace probe | API key required | Service metadata + auth state | `401` |
| GET | `/a2a/health` | A2A health probe | API key required | Health payload with checks | `401` |

## OpenAPI

- Runtime OpenAPI endpoint: `/openapi.json` on API server listener
- Static snapshot: [openapi.json](openapi.json)
