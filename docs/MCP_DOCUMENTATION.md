# MCP Server Documentation

## Transport
Primary transport: Streamable HTTP at `/mcp` unless the service documents an alternative mode in its runtime configuration.

## Authentication
Use `Authorization: Bearer <your-api-key>` or `X-API-Key: <your-api-key>`; administrative tools require an admin-capable role.

## Verification Basis
- Source files reviewed: `src/index_server/a2a_server.py`, `src/index_server/api_server.py`, `src/index_server/mcp_server.py`, `src/index_server/web_server.py`
- Tool inventory size: 60

## Tools
| Tool | Notes |
|------|-------|
| `profiles_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `profile_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_profile_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_profile_update` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_profile_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `users_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `user_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_user_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_user_update` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_user_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `groups_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `group_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_group_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_group_update` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_group_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `api_keys_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_api_key_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_api_key_revoke` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `a2a_config_events` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `collections_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `collection_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_collection_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_collection_update` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_collection_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `source_configs_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `source_config_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_source_config_create` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_source_config_update` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_source_config_delete` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `rbac_bindings_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_rbac_bind` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `admin_rbac_unbind` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_upload` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_text` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_reference` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `parsers_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `parser_test` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_preview` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `extract_only` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ocr_run` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `table_extract` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_stream_open` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_stream_event` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `ingest_stream_close` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `search` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `retrieve` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `search_explain` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_list` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_get` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_wait` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_stream` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_cancel` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `job_retry` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `queue_status` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `delete_by_id` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `delete_by_filter` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `retention_run` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `reindex_run` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `backend_health_check` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |
| `embedding_health_check` | Source-verified MCP tool name. Input and output schemas are enforced in the server runtime. |

## Example Call
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/list",
  "params": {}
}
```

## Example Response
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "tools": [
      {
        "name": "tool_name",
        "description": "What the tool does",
        "inputSchema": {"type": "object"}
      }
    ]
  }
}
```
