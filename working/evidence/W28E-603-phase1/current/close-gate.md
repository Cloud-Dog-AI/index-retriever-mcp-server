# W28E-603 — CLOSE GATE

Generated after the final evidence freeze, final commit, final push, and final tag creation.

## Deliverable
W28E-603 IndexRetriever 2.0 document-structure intelligence across the in-repo phases of design brief §24:
- **Phase 1** — Model & Persistence foundation (structure documents/sections/blocks/tables, corpus + pattern +
  template tables, Alembic migrations, RBAC-scoped service/repository).
- **Phases 2–3** — Structure extraction (internal + mineru/marker_mcp/docling providers via `cloud_dog_vdb`),
  text/IR normalisation, VDB-record/chunk linkage (§25 #6).
- **Phases 4–5** — Corpus pattern analysis (section/style/layout/table) and template generation/export
  (markdown + json).
Surfaced over MCP tools/call, REST `/api/v1/structure/*`, A2A skills, and the server-rendered admin UI.
Also fixes the four pre-existing index-retriever failures under this lane (RC-01, RC-09, IT1_21, IT1_22) and
the ST1_14 test update.

## Gate
- Every requirement in `requirements-map.tsv`: PASS (31 rows, final column PASS for every row).
- Full pytest suite (live backends where applicable): unit **211**, quality **47**, plus security/parser/
  contract/integration/system/application tiers — 0 failed. Phase 2–5 extraction/corpus/template/linkage tests
  run offline-deterministic (internal provider + sqlite). 2 system matrix legs skipped on an infrastructure
  credential boundary (dev DB rejects this host).
- §1.4 bespoke grep over structure modules + connectors: zero matches.
- MCP tool catalogue: 90 tools (UT1_40 asserts `== 90`); `structure_link_to_vdb_records` present.
- Real platform validator `final-evidence-validator.sh`: result saved as `final-evidence-validator.txt`.
- Branch + tags `W28E-603-phase1-evidence` / `W28E-603-phase1-final` pushed to GitLab; HEAD equals the remote
  branch head; the final tag is an ancestor of the remote branch head.
- Checksums: `sha256sum -c CHECKSUMS.sha256` — 44 files OK.

## §25 acceptance-criteria coverage — 14/15 PASS; #13 owed in-lane (HELD)
See `acceptance-criteria-coverage.md` for the per-criterion evidence.
- **PASS (14):** #1 #2 #3 #4 #5 #6 #7 #8 #9 #10 #11 #12 #14 #15.
  - #5 (full SQL dialect matrix) is proven against **real** backends — sqlite + Postgres 16 + MariaDB 11 —
    CRUD + Alembic migrations round-trip green on disposable ephemeral containers (server2 docker, isolated
    network). See `db-matrix-proof.txt`. A `cloud_dog_db.config.to_sync_url()` password-masking defect was
    found and recorded there (owner: cloud_dog_db package maintainer; worked around with trust/empty-auth
    disposable DBs since authentication is outside §25 #5).
- **NOT MET (1) — #13:** db-mcp-service reads/presents the structure DB. The earlier "delegate the db-mcp
  residual to another lane" decision is **WITHDRAWN** by the coordinator (moving functionality right is
  rejected). #13 is **owed inside W28E-603** and must be implemented and proven **end-to-end through the live
  db-mcp stack**: read-only-RBAC-through-stack (analyst data.read PASS / data.create 403 over the live MCP
  surface) **and** audit-source attribution (a captured live audit record identifying access as db-mcp-service).
  Only the read/present half is proven so far (`db-mcp-read-proof.txt`, bare connector — bypasses the RBAC/audit
  server layer, so not end-to-end). That path runs through db-mcp, so **W28A-871 (DB-MCP UAT WebUI recovery) is
  a HARD prerequisite** and is currently RUNNING. In-lane plan: `db-mcp-13-inlane-plan.md`. Decision of record:
  `../../W28E-603-AUDITOR-DECISION-CRITERION-13-2026-06-05.md`.

## Verdict
W28E-603 is **HELD / RUNNING at 14/15**. #13 is genuine in-lane work, blocked on W28A-871 (RUNNING); the lane
will assert `HAVE_ALL_REQUIREMENTS_BEEN_MET: YES` only when all 15 §25 criteria are genuinely met (W28A-871
lands, then #13 is implemented and proven end-to-end live in this lane). W28E-603 does not ride the W28E-618
deploy.

HAVE_ALL_REQUIREMENTS_BEEN_MET: NO  (14/15 §25 met; #13 owed in-lane — read-only-RBAC-through-stack + audit-source proven end-to-end live; HELD, hard-gated on W28A-871 which is RUNNING)
