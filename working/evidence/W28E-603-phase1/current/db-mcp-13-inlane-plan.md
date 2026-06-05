# W28E-603 §25 #13 — IN-LANE completion plan (owed by W28E-603; hard-gated on W28A-871)

Per the corrected coordinator decision (`../../W28E-603-AUDITOR-DECISION-CRITERION-13-2026-06-05.md`): #13 is
owed **inside W28E-603** and proven **end-to-end through the live db-mcp stack** — not delegated, not gated to
the right. This file is W28E-603's own work plan, blocked until W28A-871 lands.

## #13 acceptance (design brief §16) — what "met" requires, end-to-end live
1. A read-only structure profile on the **live** db-mcp-service points at the same `cloud_dog_db` structure DB.
2. Read-only RBAC enforced through the running server stack: analyst (catalog.read + data.read) can
   `catalog.list_entities` + `data.read` the structure tables (PASS); a write (`data.create`) as analyst is
   refused (403). Proven over the live MCP/API surface, not a bare connector.
3. Audit-source attribution: a captured audit record from a live read identifies access as db-mcp-service
   (distinct from IndexRetriever). If the `service_name="db-mcp-server"` envelope does not satisfy §16,
   implement explicit `Actor(type="service", id="db-mcp-service")` and prove it with a captured record.
4. Structure model version surfaced (DB-schema side met via `structure_documents.schema_version`).

## Already proven (partial, read-path only — does NOT close #13)
`db-mcp-read-proof.txt`: db-mcp-server's own `PostgreSQLConnectorBase` discovered all 12 `structure_*` tables and
read a seeded row (`schema_version 1.0`) read-only with no IndexRetriever call. This is the read/present half;
it bypasses the RBAC/audit server layer, so it is not end-to-end and not sufficient for #13.

## Hard prerequisite — W28A-871 (RUNNING)
#13's end-to-end proof requires a recovered, live db-mcp stack (api+mcp) with smoke green. W28A-871 (DB-MCP UAT
WebUI recovery & deploy smoke gate) is RUNNING, not yet accepted. db-mcp CONTEXT-SUMMARY shows lifecycle/health
work in progress (e.g. `/health` readiness). W28E-603 holds at 14/15 until W28A-871 lands.

## W28E-603 execution sequence once W28A-871 is accepted
1. Bring up the recovered live db-mcp stack (per W28A-871 deploy state).
2. Create the read-only structure profile; run the live RBAC matrix (analyst data.read PASS / data.create 403)
   over MCP — capture conformance + audit records.
3. Confirm or implement audit-source attribution; capture the audit record proving the source.
4. Add the end-to-end conformance test + evidence; flip #13 → met; only then assert HAVE_ALL: YES.
