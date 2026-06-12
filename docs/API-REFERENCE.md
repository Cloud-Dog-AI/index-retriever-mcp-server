---
template-id: T-API
template-version: 1.0
applies-to: docs/API-REFERENCE.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-12
doc-git-commit: 5cba8eb76245a4d7ba5af6f0b3b765199a6f6ee6
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# index-retriever-mcp-server — API-REFERENCE

> **Template version:** T-API v1.0 — REST surface authoritative reference. `openapi.json` is build-generated; this doc explains it.

## 1. Auth model
Auth modes accepted (`api_key`, `cookie`, `vault-bootstrap`), header name, RBAC mapping.

## 2. Routes

**You MUST include:** every route registered by the service. Group by section: Auth / Admin / Data / Health.

| Method | Path | Auth | RBAC | Summary | Request | Response |
|---|---|---|---|---|---|---|
| GET | `/health` | none | n/a | liveness | — | `{status:"ok"}` |

## 3. Error model
Standard error envelope, status codes, retryability.

## 4. Examples
**You MUST include:** at least one worked curl example per route group.

```
curl -H "X-API-Key: ${API_KEY}" https://<host>/api/v1/<route>
```

## 5. Cross-references
- [openapi.json](openapi.json)
- [MCP-REFERENCE.md](MCP-REFERENCE.md)
- [A2A-REFERENCE.md](A2A-REFERENCE.md)
- [WEBUI-REFERENCE.md](WEBUI-REFERENCE.md)
- PS-20-api.md

## 6. Project-specific notes
