---
template-id: T-MCP
template-version: 1.0
applies-to: docs/MCP-REFERENCE.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-18
doc-git-commit: 16fd5b2c0000000000000000000000000000000000
doc-git-branch: main
doc-source-shas:
  - src/index_tools/tools/registry.py
  - src/index_tools/tools/definitions.py
  - src/index_server/mcp_server.py
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-18T00:00:00Z
---

# index-retriever-mcp-server — MCP-REFERENCE

> **Template version:** T-MCP v1.0 — MCP tool surface (JSON-RPC 2.0 at `/mcp`).

Tool count: **93** — all verified as string literals in `src/index_tools/tools/registry.py`.

## 1. Auth model

Auth mode: `apikey+jwt` (`CLOUD_DOG__AUTH__MODE`). The MCP endpoint at `/mcp` accepts:
- `X-API-Key: <key>` header (API key bound to a principal with roles).
- `Authorization: Bearer <jwt>` header (JWT validated against JWKS).

RBAC mapping (`src/index_server/mcp_server.py:194-276`): each tool resolves to a required
permission (`admin`, `collection.read`, `collection.write`, or `source.configure`). The
auth middleware checks the caller's resolved role against that permission. Tools prefixed
`admin_` and the identity-management tools (`users_list`, `user_get`, etc.) require `admin`.
Read tools require `collection.read` (minimum role: `viewer`/`read-only`). Write/ingest tools
require `collection.write` (minimum role: `user`/`read-write`). Parser-test tools require
`source.configure`. Default deny: unauthenticated callers receive `401`; under-privileged
callers receive `403`.

RBAC role summary:

| Permission | Minimum runtime role | Flat-login alias |
|---|---|---|
| `admin` | `admin` | `admin` |
| `collection.write` | `user` | `read-write` |
| `collection.read` | `viewer` | `read-only` |
| `source.configure` | `user` | `read-write` |

## 2. Tools

All tools are invoked via JSON-RPC 2.0 POST to `/mcp`:

```bash
curl -X POST https://<host>/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"profiles_list","arguments":{...}},"id":1}'
```

---

### 2.1 `profiles_list`

- **Description:** List all configured profiles with their embedding and backend settings.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401` unauthenticated, `403` insufficient role.

---

### 2.2 `profile_get`

- **Description:** Retrieve a single profile by its identifier.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` profile not found.

---

### 2.3 `admin_profile_create`

- **Description:** Create a new profile with embedding model and backend configuration.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `409` profile already exists.

---

### 2.4 `admin_profile_update`

- **Description:** Update an existing profile's settings.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` profile not found.

---

### 2.5 `admin_profile_delete`

- **Description:** Delete a profile and its associated configuration.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` profile not found.

---

### 2.6 `users_list`

- **Description:** List all registered users with their roles and group memberships.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.7 `user_get`

- **Description:** Retrieve a single user record by user ID.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` user not found.

---

### 2.8 `admin_user_create`

- **Description:** Create a new user with specified roles and group memberships.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `409` user already exists.

---

### 2.9 `admin_user_update`

- **Description:** Update an existing user's display name, roles, or groups.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` user not found.

---

### 2.10 `admin_user_delete`

- **Description:** Delete a user and revoke their access.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` user not found.

---

### 2.11 `groups_list`

- **Description:** List all groups with their roles and member lists.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.12 `group_get`

- **Description:** Retrieve a single group by group ID.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` group not found.

---

### 2.13 `admin_group_create`

- **Description:** Create a new group with specified roles and members.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `409` group already exists.

---

### 2.14 `admin_group_update`

- **Description:** Update a group's roles or membership list.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` group not found.

---

### 2.15 `admin_group_delete`

- **Description:** Delete a group.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` group not found.

---

### 2.16 `api_keys_list`

- **Description:** List all API keys with their labels, roles, and revocation status.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.17 `admin_api_key_create`

- **Description:** Create a new API key bound to a user with specified roles.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.18 `admin_api_key_revoke`

- **Description:** Revoke an API key, immediately disabling its access.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` key not found.

---

### 2.19 `a2a_config_events`

- **Description:** Retrieve the log of admin configuration change events for A2A consumers.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.20 `index_list`

- **Description:** List indexed collections for the selected profile.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.21 `collections_list`

- **Description:** List all collections, optionally filtered by profile.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.22 `list_collections`

- **Description:** List all collections, optionally filtered by profile. Alias for `collections_list`.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.23 `collection_get`

- **Description:** Retrieve a single collection's metadata, dimensions, and access roles.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` collection not found.

---

### 2.24 `admin_collection_create`

- **Description:** Create a new vector collection within a profile.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `409` collection already exists.

---

### 2.25 `admin_collection_update`

- **Description:** Update a collection's description, metadata, or access roles.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` collection not found.

---

### 2.26 `admin_collection_delete`

- **Description:** Delete a collection and its stored vectors.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` collection not found.

---

### 2.27 `source_configs_list`

- **Description:** List all source configurations for connectors and ingestion schedules.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.28 `source_config_get`

- **Description:** Retrieve a single source configuration by its ID.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` source config not found.

---

### 2.29 `admin_source_config_create`

- **Description:** Create a new source configuration with URI, schedule, and metadata.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.30 `admin_source_config_update`

- **Description:** Update an existing source configuration.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` source config not found.

---

### 2.31 `admin_source_config_delete`

- **Description:** Delete a source configuration.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` source config not found.

---

### 2.32 `hdro_extract`

- **Description:** Fetch HDI/GII records from the UNDP HDRO Data API 2.0 using the Vault-backed HDRO API key.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "country_or_aggregation": {"type": "string", "default": "AFG"},
      "year": {"type": "integer", "default": 2022},
      "indicators": {"type": "array", "items": {"type": "string"}, "default": ["HDI", "GII"]},
      "limit": {"type": "integer", "default": 20}
    },
    "required": ["country_or_aggregation", "year", "indicators", "limit"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "source_family": {"type": "string"},
      "canonical_base_url": {"type": "string"},
      "base_url": {"type": "string"},
      "endpoint_host": {"type": "string"},
      "endpoint_path": {"type": "string"},
      "redacted_request_url": {"type": "string"},
      "country_or_aggregation": {"type": "string"},
      "year": {"type": "string"},
      "supported_indicators": {"type": "array"},
      "requested_indicators": {"type": "array"},
      "records": {"type": "array"},
      "record_count": {"type": "integer"},
      "raw_record_count": {"type": "integer"}
    }
  }
  ```
- **Errors:** `401`, `403`, `502` upstream HDRO API unreachable.

---

### 2.33 `rbac_bindings_list`

- **Description:** List all RBAC role bindings for users and groups.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.34 `admin_rbac_bind`

- **Description:** Bind a role to a user or group entity.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.35 `admin_rbac_unbind`

- **Description:** Remove a role binding from a user or group entity.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` binding not found.

---

### 2.36 `ingest_upload`

- **Description:** Upload a file for chunking, embedding, and indexing into a collection.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "job_id": {"type": "string"},
      "status": {"type": "string"}
    },
    "required": ["job_id", "status"]
  }
  ```
- **Errors:** `401`, `403`, `413` file too large.

---

### 2.37 `bulk_index`

- **Description:** Queue one or more text documents for asynchronous indexing into a collection.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.38 `ingest_text`

- **Description:** Ingest inline text content into a profile and collection.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "profile": {"type": "string"},
      "collection": {"type": "string"},
      "text": {"type": "string"},
      "source": {"type": "string", "default": "inline"}
    },
    "required": ["profile", "collection", "text"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "job_id": {"type": "string"},
      "status": {"type": "string"}
    },
    "required": ["job_id", "status"]
  }
  ```
- **Errors:** `401`, `403`, `422` validation error.

---

### 2.39 `ingest_reference`

- **Description:** Ingest content from a URI reference via a configured connector.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "profile": {"type": "string"},
      "collection": {"type": "string"},
      "path": {"type": "string", "default": ""},
      "uri": {"type": "string", "default": ""}
    },
    "required": ["profile", "collection"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "job_id": {"type": "string"},
      "status": {"type": "string"}
    },
    "required": ["job_id", "status"]
  }
  ```
- **Errors:** `401`, `403`, `422` bad URI, `502` connector unreachable.

---

### 2.40 `parsers_list`

- **Description:** List available document parsers and their supported MIME types.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "parser_services": {"type": "object", "default": {}}
    }
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "parsers": {"type": "array", "items": {"type": "object"}}
    }
  }
  ```
- **Errors:** `401`, `403`.

---

### 2.41 `parser_test`

- **Description:** Test a parser against sample content and return extraction results.
- **RBAC:** `source.configure` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "provider_id": {"type": "string"},
      "sample_text": {"type": "string", "default": "parser health check"},
      "source_uri": {"type": "string", "default": "inline://parser-test.txt"},
      "parser_services": {"type": "object", "default": {}},
      "options": {"type": "object", "default": {}}
    },
    "required": ["provider_id"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "provider_id": {"type": "string"},
      "provider_version": {"type": "string"},
      "healthy": {"type": "boolean"},
      "text_blocks": {"type": "integer"},
      "table_blocks": {"type": "integer"},
      "quality": {"type": "object"}
    }
  }
  ```
- **Errors:** `401`, `403`, `502` parser service unreachable.

---

### 2.42 `ingest_preview`

- **Description:** Preview how content will be chunked and embedded without persisting.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "text": {"type": "string"},
      "source_uri": {"type": "string", "default": "inline://preview.txt"},
      "parser_chain": {"type": "array", "items": {"type": "string"}},
      "parser_options": {"type": "object"},
      "parser_services": {"type": "object"},
      "metadata": {"type": "object"},
      "ocr_mode": {"type": "string", "default": "disabled"},
      "ocr_provider": {"type": "string", "default": ""},
      "table_policy": {"type": "string", "default": "table_as_markdown"},
      "table_json_shape": {"type": "string", "default": "records"}
    },
    "required": ["text"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "source_uri": {"type": "string"},
      "filename": {"type": "string"},
      "mime_type": {"type": "string"},
      "chunk_count": {"type": "integer"},
      "parser_provider": {"type": "string"},
      "parser_version": {"type": "string"},
      "ocr_mode": {"type": "string"},
      "checkpoints": {"type": "array"}
    }
  }
  ```
- **Errors:** `401`, `403`, `422` validation error.

---

### 2.43 `extract_only`

- **Description:** Extract text and metadata from a document without chunking or indexing.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:** Same as `ingest_preview`.
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "source_uri": {"type": "string"},
      "text": {"type": "string"},
      "chunk_count": {"type": "integer"},
      "parser_provider": {"type": "string"},
      "ocr_applied": {"type": "boolean"},
      "table_policy": {"type": "string"}
    }
  }
  ```
- **Errors:** `401`, `403`, `422`.

---

### 2.44 `ocr_run`

- **Description:** Run OCR on an image or scanned document and return extracted text.
- **RBAC:** `source.configure` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "text": {"type": "string"},
      "mode": {"type": "string", "default": "auto"},
      "provider_id": {"type": "string", "default": ""},
      "min_chars": {"type": "integer", "default": 200},
      "min_scanned_ratio": {"type": "number", "default": 0.5},
      "scanned_ratio": {"type": "number", "default": 0.0}
    },
    "required": ["text"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "enabled": {"type": "boolean"},
      "mode": {"type": "string"},
      "reason": {"type": "string"},
      "provider_id": {"type": "string"}
    }
  }
  ```
- **Errors:** `401`, `403`, `502` OCR provider unreachable.

---

### 2.45 `table_extract`

- **Description:** Extract structured table data from a document.
- **RBAC:** `source.configure` (user / read-write or above)
- **Input schema:** Same as `ingest_preview`.
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "source_uri": {"type": "string"},
      "table_policy": {"type": "string"},
      "table_json_shape": {"type": "string"},
      "table_count": {"type": "integer"},
      "tables": {"type": "array", "items": {"type": "string"}},
      "parser_provider": {"type": "string"}
    }
  }
  ```
- **Errors:** `401`, `403`, `422`.

---

### 2.46 `ingest_stream_open`

- **Description:** Open a streaming ingestion session for incremental content delivery.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.47 `ingest_stream_event`

- **Description:** Send a content event to an open streaming ingestion session.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "job_id": {"type": "string"},
      "status": {"type": "string"}
    }
  }
  ```
- **Errors:** `401`, `403`, `404` session not found.

---

### 2.48 `ingest_stream_close`

- **Description:** Close a streaming ingestion session and finalise indexing.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` session not found.

---

### 2.49 `search`

- **Description:** Perform a semantic vector search within a profile and collection.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "profile": {"type": "string"},
      "collection": {"type": "string"},
      "query": {"type": "string"},
      "top_k": {"type": "integer", "default": 10},
      "filters": {"type": "object", "default": {}}
    },
    "required": ["profile", "collection", "query"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "doc_id": {"type": "string"},
            "chunk_id": {"type": "string"},
            "text": {"type": "string"},
            "score": {"type": "number"},
            "source_uri": {"type": "string"},
            "metadata": {"type": "object"}
          }
        }
      }
    }
  }
  ```
- **Errors:** `401`, `403`, `404` collection not found.

---

### 2.50 `retrieve`

- **Description:** Retrieve a specific document by ID from a profile and collection.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "profile": {"type": "string"},
      "collection": {"type": "string"},
      "doc_id": {"type": "string"}
    },
    "required": ["profile", "collection", "doc_id"]
  }
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "doc_id": {"type": "string"},
      "profile": {"type": "string"},
      "collection": {"type": "string"},
      "source": {"type": "string"},
      "source_uri": {"type": "string"},
      "text": {"type": "string"},
      "lifecycle_state": {"type": "string"},
      "metadata": {"type": "object"}
    }
  }
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.51 `search_explain`

- **Description:** Perform a search with scoring explanation and relevance breakdown.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:** Same as `search`.
- **Output schema:** Same as `search` with additional per-result explanation fields.
- **Errors:** `401`, `403`, `404` collection not found.

---

### 2.52 `job_list`

- **Description:** List all jobs with their current status and metadata.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.53 `job_get`

- **Description:** Retrieve a single job's status, progress, and result.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` job not found.

---

### 2.54 `job_wait`

- **Description:** Block until a job completes or times out, then return its result.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` job not found, `408` timeout.

---

### 2.55 `job_stream`

- **Description:** Stream real-time progress events from a running job.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:** SSE stream of job progress events.
- **Errors:** `401`, `403`, `404` job not found.

---

### 2.56 `job_cancel`

- **Description:** Cancel a queued or running job.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` job not found.

---

### 2.57 `job_retry`

- **Description:** Retry a failed or cancelled job with the same parameters.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` job not found.

---

### 2.58 `job_delete`

- **Description:** Delete a terminal job record.
- **RBAC:** `admin`
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` job not found.

---

### 2.59 `queue_status`

- **Description:** Return queue depth, running job count, and backend health status.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.60 `w28a_693_lifecycle_job`

- **Description:** Create a source-backed W28A-693 lifecycle evidence job through the index-retriever queue runtime.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "outcome": {"type": "string"},
      "job_type": {"type": "string", "default": "ingest_text"},
      "label": {"type": "string", "default": ""},
      "profile": {"type": "string", "default": "default"},
      "collection": {"type": "string", "default": "w28a_693"}
    },
    "required": ["outcome"]
  }
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.61 `delete_by_id`

- **Description:** Delete a specific document from a collection by its ID.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.62 `delete_by_filter`

- **Description:** Delete documents matching a metadata filter from a collection.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.63 `retention_run`

- **Description:** Execute retention policy to remove expired or stale documents.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.64 `reindex_run`

- **Description:** Re-embed and re-index existing documents in a collection.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.65 `backend_health_check`

- **Description:** Check connectivity and health of the vector database backend.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "provider": {"type": "string"},
      "backend": {"type": "string"}
    }
  }
  ```
- **Errors:** `401`, `403`, `502` backend unreachable.

---

### 2.66 `embedding_health_check`

- **Description:** Check connectivity and health of the embedding model provider.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "provider": {"type": "string"},
      "model": {"type": "string"},
      "dimensions": {"type": "integer"}
    }
  }
  ```
- **Errors:** `401`, `403`, `502` embedder unreachable.

---

### 2.67 `ingest_health`

- **Description:** Return per-profile ingest pipeline health: queue depth, concurrency slots, embedder warm status, and last ingest latency.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.68 `file_upload`

- **Description:** Upload a file to service storage. Returns file_id and metadata.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `413` file too large.

---

### 2.69 `file_list`

- **Description:** List stored files with optional profile/collection filter.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.70 `file_get`

- **Description:** Get metadata for a stored file by ID.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` file not found.

---

### 2.71 `file_download`

- **Description:** Download stored file content by ID. Returns base64-encoded content.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` file not found.

---

### 2.72 `file_delete`

- **Description:** Delete a stored file by ID.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` file not found.

---

### 2.73 `structure_health`

- **Description:** Report document-structure subsystem health, including the canonical structure store probe.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.74 `structure_document_create`

- **Description:** Create or idempotently replace a canonical document-structure record (document plus pages/blocks/sections/styles/tables/figures/relations).
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `422` validation error.

---

### 2.75 `structure_document_get`

- **Description:** Retrieve a canonical structure document by its structure_document_id, optionally including child objects.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.76 `structure_document_list`

- **Description:** List canonical structure documents, filtered by profile, collection or status, with pagination.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.77 `structure_document_delete`

- **Description:** Delete a canonical structure document and all of its child objects.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.78 `structure_outline_get`

- **Description:** Return the section hierarchy (outline) for a structure document as a nested tree.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.79 `structure_pages_list`

- **Description:** List page-level layout records for a structure document.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.80 `structure_sections_list`

- **Description:** List section records for a structure document.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

### 2.81 `structure_extract`

- **Description:** Extract canonical document structure from text or a file via a parser provider (internal/mineru/marker/docling) and persist it.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `422`, `502` parser provider unreachable.

---

### 2.82 `structure_corpus_create`

- **Description:** Create a named corpus (set of structure documents) for cross-document analysis.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `409` corpus already exists.

---

### 2.83 `structure_corpus_list`

- **Description:** List structure corpora, optionally filtered by profile.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.84 `structure_corpus_get`

- **Description:** Retrieve a single corpus by id.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.85 `structure_corpus_update`

- **Description:** Update a corpus (name, description, member documents).
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.86 `structure_corpus_delete`

- **Description:** Delete a corpus and its derived patterns.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.87 `structure_corpus_analyse`

- **Description:** Analyse a corpus to derive section/style/layout/table patterns and a report.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.88 `structure_corpus_patterns_get`

- **Description:** Retrieve derived patterns for a corpus, optionally filtered by pattern type.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.89 `structure_template_generate`

- **Description:** Generate a reusable structure/style template blueprint from a corpus's patterns.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` corpus not found.

---

### 2.90 `structure_template_get`

- **Description:** Retrieve a generated template by id.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` template not found.

---

### 2.91 `structure_template_list`

- **Description:** List generated templates, optionally filtered by profile or corpus.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`.

---

### 2.92 `structure_template_export`

- **Description:** Export a template as Markdown or JSON.
- **RBAC:** `collection.read` (viewer / read-only or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` template not found.

---

### 2.93 `structure_template_delete`

- **Description:** Delete a generated structure template through the supported lifecycle path.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"template_id":{"type":"string"}},"required":["template_id"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"template_id":{"type":"string"},"deleted":{"type":"boolean"},"corpus_id":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` template not found.

---

### 2.94 `structure_link_to_vdb_records`

- **Description:** Link a structure document to existing VDB record/chunk ids and source document.
- **RBAC:** `collection.write` (user / read-write or above)
- **Input schema:**
  ```json
  {"type":"object","properties":{"profile":{"type":"string"},"collection":{"type":"string"}},"required":["profile","collection"]}
  ```
- **Output schema:**
  ```json
  {"type":"object","properties":{"status":{"type":"string"}}}
  ```
- **Errors:** `401`, `403`, `404` document not found.

---

## 3. Cross-references

- [API-REFERENCE.md](API-REFERENCE.md)
- [A2A-REFERENCE.md](A2A-REFERENCE.md)
- PS-72-mcp-a2a-webui.md

## 4. Project-specific notes

All tool names listed in this document exist as string literals in
`src/index_tools/tools/registry.py` (`build_default_tool_registry`). The permission
mapping is canonical in `src/index_server/mcp_server.py:194-276`
(`_required_permission_for_tool`). The MCP endpoint is at port `8076` (default,
`CLOUD_DOG__MCP_SERVER__PORT`). The web tier at port `8075` proxies `/mcp` to the
MCP server and `/api/v1/tools` for tool listing/dispatch.
