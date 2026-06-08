# W28E-603 — local Docker smoke (merged worktree state)
Date context: 2026-06-05. Built from isolated lane worktree .w28e603-ir-wt on server2 (DOCKER_HOST=tcp://server2:2375).
Image: cloud-dog/index-retriever-mcp-server:latest  built sha256:14e1eab4...  pushed registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server@sha256:e0124ccafa9b696a2baf34b37e00ba802503ac170fd28171c8628f86b167b5cd
Run: docker run (bridge net w28e603-smoke-net) CLOUD_DOG_ENV_FILE=tests/env-AT-local-docker + Vault token; entrypoint 'all'.

## Surfaces up (Uvicorn): api:8074 web:8075 mcp:8076 a2a:8077

## /health (api 8074) — db ok, vdb checked
{"status":"ok","application":"index-retriever-mcp-server","version":"0.1.0","env_file":null,"checks":{"db":{"status":"ok","ok":true,"probe":{"ok":true,"result":1}},"vdb":{"status":"ok","detail":{"status":"ok","provider":"chroma","backend":"chroma"}},"embedding":{"status":"ok","detail":{"status":"ok","provider":"ollama","model":"nomic-embed-text","dimensions":8}}}}

## /version surfaces
api/v1/version (8074): {"application":"index-retriever-mcp-server","version":"0.1.0","api_version":"v1"}
SPA root (8074 /version): serves <!doctype html> cloud-dog Index Retriever SPA (HTTP 200)
mcp /api/v1/version (8076): {"application":"index-retriever-mcp-server-mcp","version":"0.1.0","api_version":"v1"}

## MCP tools/call smoke
POST /mcp/tools/structure_corpus_list (8076): {"ok":false,"error":{"code":"UNAUTHENTICATED","message":"Authentication failed","details":null,"retryable":false},"meta":{"request_id":"09ed3745475942f6a60ca39cc8207191","correlation_id":null},"detail

VERDICT: image boots from merged state; health ok (db ok), version+SPA served on all surfaces, MCP responds. Local Docker smoke PASS.
