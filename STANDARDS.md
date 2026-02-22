# index-retriever-mcp-server — Standards Mapping

## Applicable standards

1. PS-00 Engineering Principles: API-first architecture, no hardcoded values, UK English, strong testability.
2. PS-10 Architecture: strict split between `src/index_tools/` library and `src/index_server/` transport layer.
3. PS-20 API Contracts: canonical HTTP interface with health, consistent errors, and correlation IDs.
4. PS-40 Logging and Observability: structured operational logs and append-only audit logging.
5. PS-50 LLM Interfaces: embedding integration only through `cloud_dog_llm` adapters.
6. PS-60 Vector DB Interfaces: vector backends only through `cloud_dog_vdb` adapters.
7. PS-70 User Management and IDAM: authentication and RBAC through `cloud_dog_idam`.
8. PS-75 Job Queue: ingestion and maintenance jobs through `cloud_dog_jobs`.
9. PS-80 Configuration Management: configuration loading and vault delegation through `cloud_dog_config`.
10. PS-90 Security: default-deny connector scopes, secret redaction, and least-privilege runtime.

## Testing standard note

Test hierarchy and `--env` enforcement follow PS-95 as specified in `TESTS.md` and `tests/conftest.py`.
