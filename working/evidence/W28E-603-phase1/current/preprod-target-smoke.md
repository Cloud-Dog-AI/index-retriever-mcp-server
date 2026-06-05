# W28E-603 — preprod target smoke (indexretriever0)
Date context: 2026-06-05. Service: https://indexretriever0.cloud-dog.net (live, post-deploy).

## /health (all backends healthy on preprod)
{"status":"ok","application":"index-retriever-mcp-server","version":"0.1.0","env_file":null,"checks":{"db":{"status":"ok","ok":true,"probe":{"ok":true,"result":1}},"vdb":{"status":"ok","detail":{"status":"ok","provider":"qdrant","backend":"qdrant"}},"embedding":{"status":"ok","detail":{"status":"ok","provider":"ollama","model":"nomic-embed-text","dimensions":8}}}}

## /api/v1/version
{"application":"index-retriever-mcp-server","version":"0.1.0","api_version":"v1"}
## SPA root: serves <!doctype html> cloud-dog Index Retriever (HTTP 200)
## structure routes deployed (auth-gated, not 404 => present):
  GET /api/v1/structure/corpora -> 401
  POST /mcp/tools/structure_corpus_list -> 401

VERDICT: preprod deploy + smoke PASS — health ok (db/vdb/embedding), version+SPA served, structure routes/MCP tools deployed.
