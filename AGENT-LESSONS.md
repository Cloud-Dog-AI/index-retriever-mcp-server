# index-retriever-mcp-server — Local Agent Lessons

> **Common authority:** Read [Platform Rules](../cloud-dog-ai-platform-standards/RULES.md) and [Platform Lessons](../cloud-dog-ai-platform-standards/AGENT-LESSONS.md) first. This file adds local facts only; it cannot weaken common policy.

Platform Standards owns common policy. This overlay owns ingest/retrieval/VDB facts.

- Prove ingest idempotency with first/second real runs: stable collection/document/
  record IDs, stable hashes, no duplicate objects and reduced external fetches.
- Bind every returned result to its actual source URI and VDB collection/document/
  record identifiers; reject display-only or orphaned results.
- Exercise real authenticated API, MCP tool call and A2A task, plus required
  negatives; health, card and tools-list responses are not functional proof.

- Preserve ingest/delete/search/retrieve lifecycle shaping across surfaces; clear cached runtime configuration when tests mutate environment/configuration.
- A controller-local source path is not a service-visible source. Prove each profile through list, ingest, completion, same-profile search and restart/redeploy durability.
- Derive current API/legacy/rejected paths and metadata fields from source and requirements; the named full native suite remains the required cross-layer gate when instructed.

Evidence: first/second ingest ledger; query-binding audit; API/MCP/A2A matrix;
local/final-PREPROD Playwright and identity chain.

- **Listener ports.** API `8074`, Web `8075`, MCP `8076` and A2A `8077` are this service's default listener allocation. Read current `defaults.yaml` and the authorised environment overlay before use; never use the retired bootstrap table or guess an override.
- **Bootstrap-seed secret exception.** `config/bootstrap-seed.yaml` may name an operator-supplied `token_env_var` for an admin seed secret; the annotated bootstrap resolver may read only that dynamic secret. Never place an inline token in the seed/configuration or extend this exception to non-secret bootstrap settings.
