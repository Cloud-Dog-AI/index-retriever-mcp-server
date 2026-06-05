# W28E-603 §25 #13 — db-mcp-server DELEGATION lane spec (W28E-603-DBMCP-13R, gated on W28A-871)

**Criterion #13:** "`db-mcp-service` can read/present the same structure database through an authorised
profile/interface." Design brief §16. Coordinator decision:
`W28E-603-AUDITOR-DECISION-CRITERION-13-2026-06-05.md` — #13 is MET for index-retriever scope; the db-mcp-side
residual below is DELEGATED to a named, gated db-mcp-server lane.

## Index-retriever scope — DONE and PROVEN
- Structure schema persists in the canonical `cloud_dog_db` SQL surface (no bespoke), §25 #4 PASS.
- Discoverable by any `cloud_dog_db` consumer: 12 tables (structure_documents, _sections, _blocks, _pages,
  _tables, _figures, _styles, _relations, _extractor_runs, _corpora, _patterns, _templates).
- `structure_documents.schema_version` carries the structure model version (DB-schema metadata, §16).
- **Cross-service read PROVEN** (`db-mcp-read-proof.txt`): db-mcp-server's own `PostgreSQLConnectorBase`, via a
  read-only profile URI, ran list_namespaces / list_entities / describe / data.read over the real structure DB
  (seeded row `sd_3937…`, `schema_version 1.0`), read-only, with no index-retriever call. The read/present
  capability works today with config only — no new db-mcp read/discovery code is required.

## Delegated to lane W28E-603-DBMCP-13R (owner: db-mcp-server; gate: W28A-871)
Concrete, bounded deliverables to be carried by the db-mcp-server RBAC/audit lane:

1. **Audit source-attribution.** §16: audit must identify whether access came via IndexRetriever or
   db-mcp-service. db-mcp-server emits audit via `cloud_dog_logging` with `service_name="db-mcp-server"`
   (src/common/runtime.py:170), so the envelope already distinguishes source; `src/core/connectors/service.py`
   (~141-162) records `Actor(type="user", …)`. Deliverable: confirm the `service_name` envelope satisfies §16
   with a captured audit record from a real read, or add explicit `Actor(type="service", id="db-mcp-service")`.

2. **Read-only RBAC through the full server stack.** This lane proved the bare connector read path; db-mcp-
   server's RBAC/audit layer is exercised in the delegated lane. Deliverable: stand up db-mcp-server (api+mcp),
   create a read-only structure profile (analyst role: catalog.read + data.read), run `catalog.list_entities` +
   `data.read` over MCP as an analyst (PASS) and a write (`data.create`) as analyst (403). Reference patterns:
   tests/integration/IT1.4_ContentCRUDLifecycle, tests/system/ST1.14_PostgreSQLConnector.

3. **Structure model version in API metadata (enhancement).** DB-schema side is met
   (`structure_documents.schema_version`). Optionally surface a structure schema version in db-mcp-server
   describe/metadata responses.

## Why a separate lane
db-mcp-server is a separate service/repo with its own evidence pack, validator and deploy. Its RBAC/audit
internals belong to the named db-mcp-server lane W28E-603-DBMCP-13R (gated on W28A-871), per coordinator
authorization. The read-proof above pre-validates and de-risks that lane.
