# API Documentation

This file preserves the legacy API documentation path consumed by IT1.24.
The canonical endpoint detail remains in `API-REFERENCE.md`; this compatibility
document records the required externally visible contract anchors.

## Service Ports

| Service | Port |
|---|---:|
| API server | 8074 |
| Web server | 8075 |
| MCP server | 8076 |
| A2A server | 8077 |

## OpenAPI

The API server publishes its schema at `openapi.json`. Tool outputs expose
canonical parser and source metadata fields, including `parser_provider`,
`parser_version`, `ocr_engine`, `ocr_confidence`, `page`, `table_id`,
`source_uri`, `content_hash`, `lifecycle_state`, and `is_latest`.
