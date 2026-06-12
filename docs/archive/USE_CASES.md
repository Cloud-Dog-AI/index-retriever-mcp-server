# Index Retriever Use Cases

## UC-CFG-01 New Document Index Profile With Custom Embedding

1. Create a new index profile that selects vector backend, embedding model, and ingestion defaults.
2. Create a collection under that profile and ingest sample content.
3. Run retrieval queries and verify the profile-specific backend and policy are honoured.
4. Update the profile to change embedding or indexing policy.
5. Re-ingest content and verify updated retrieval behaviour.
6. Delete the profile or its collections and confirm the resources are gone.

Current status:
- MCP-admin profile lifecycle exists in the service/tool layer.
- Dedicated REST admin CRUD, WebUI parity, and user/group/API-key CRUD are not yet fully delivered.
