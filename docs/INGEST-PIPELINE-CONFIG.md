# Ingest Pipeline Config

Index-retriever supports an optional outbound enrichment step before document
metadata validation, chunking, embedding, and vector upsert.

The compact YAML form is:

```yaml
pipeline:
  - enrich: search-mcp.enrich(query=$doc.title, depth=quick)
```

The structured form is:

```yaml
enrich:
  enabled: true
  steps:
    - service: search-mcp
      tool: enrich
      transport: mcp
      required: false
      arguments:
        query: $doc.title
        depth: quick
```

Operators can store these blocks in a source config's `metadata` field. Direct
ingest callers may also pass the same metadata block for one-off runs.

Operator-default pipelines are loaded from
`dev.services.indexretriever.default_pipelines`. Entries are opt-in: an entry is
ignored unless `enabled: true`, and optional `profiles`, `collections`, and
`source_uri_globs` filters can scope the default to a tenant/profile, collection,
or source pattern.

```yaml
dev:
  services:
    indexretriever:
      default_pipelines:
        search_mcp_enrich:
          enabled: true
          profiles: ["default"]
          collections: ["research"]
          source_uri_globs: ["https://docs.example/**"]
          pipeline:
            - enrich: search-mcp.enrich(query=$doc.title, depth=quick)
              transport: a2a
              required: false
```

Outbound service endpoints and credentials are resolved through
`cloud_dog_config` at call time. By default, `search-mcp` reads its credential
from `dev.services.searchmcp0.api_key`; no credential value is stored in the
client instance.
