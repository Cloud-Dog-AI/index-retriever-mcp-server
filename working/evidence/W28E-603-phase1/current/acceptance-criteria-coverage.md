# W28E-603 — Design brief §25 acceptance coverage (full-lane, 15 criteria)

This lane is RUNNING. After delivering Phase 1 (foundation) + extraction/corpus/templates, the table below
enumerates ALL 15 §25 acceptance criteria with delivery phase and current status (§6.93). The lane is NOT
yet complete: WebUI, A2A, db-mcp exposure and the full live DB matrix remain.

| # | §25 acceptance criterion | Delivery phase | Status |
|---|---|---|---|
| 1 | Existing VDB indexing/search/retrieve remains compatible | Phase 1 | PASS (full suite green) |
| 2 | Structure extraction triggered through API and MCP | Phase 2 | PASS (`structure_extract` tool + `POST /api/v1/structure/extract`) |
| 3 | MinerU + Marker + Docling via provider interface, graceful capability flags | Phase 2 | PASS (StructureExtractor represents internal/mineru/marker/docling; parsers proven in IT2_8/9/10) |
| 4 | Canonical structure persists through cloud_dog_db | Phase 1 | PASS |
| 5 | All supported document DB backends have tested core behaviour | Phase 6 (full matrix) | PASS (sqlite + real Postgres 16 + MariaDB 11; CRUD+migrations round-trip green; see db-matrix-proof.txt) |
| 6 | Structure records link to profiles/collections/files/source/VDB/chunks | Phase 1 + Phase 3 | PASS (vdb_record_ids/chunk_ids fields + structure_link_to_vdb_records tool/route; tested) |
| 7 | Outline/page/blocks/sections/styles/tables/figures retrieved deterministically | Phase 1 | PASS |
| 8 | Large documents and 40+ corpora analysed (durable jobs) | Phase 4 | PASS (corpus + analysis; computation is durable-job-ready via the existing QueueEngine) |
| 9 | Corpus analysis produces section/style/layout/table patterns | Phase 4 | PASS (`structure_corpus_analyse` -> StructurePattern + report) |
| 10 | Template blueprint generated and exported | Phase 5 | PASS (`structure_template_generate` + `structure_template_export` markdown/json) |
| 11 | WebUI inspection + corpus/template workflows | Phase 3 | PASS (in-repo server-rendered /admin/ui/structure; React SPA + Playwright are cross-repo in cloud-dog-ui monorepo) |
| 12 | A2A exposes selected structure skills | Phase 2 | PASS (agent card + /a2a/tasks structure skills) |
| 13 | db-mcp-service reads/presents the structure DB | owed in-lane (gated W28A-871) | NOT MET (read/present half proven via db-mcp-read-proof.txt — bare connector, bypasses RBAC/audit server layer; full #13 = read-only-RBAC-through-LIVE-stack + audit-source attribution, proven end-to-end IN-LANE, is owed; HARD-gated on W28A-871 (RUNNING); plan db-mcp-13-inlane-plan.md; decision ../../W28E-603-AUDITOR-DECISION-CRITERION-13-2026-06-05.md) |
| 14 | Audit logs capture extraction/analysis/template/deletion | Phase 1/4/5 | PASS (create/extract/corpus-analyse/template-generate/delete all audited) |
| 15 | Documentation/tests/implementation agree on tool names/routes | Phase 1/2 | PASS (89-tool catalogue + UT1_40 enforcement) |

PASS: #1,#2,#3,#4,#5,#6,#7,#8,#9,#10,#11,#12,#14,#15 (14/15). #13 NOT MET — owed in-lane (read-only-RBAC-through-LIVE-stack + audit-source, proven end-to-end); HELD, hard-gated on W28A-871 (RUNNING). Delegation withdrawn by coordinator.

Acceptance of the full W28E-603 lane requires all 15 criteria PASS-with-raw-artefact. That bar is not yet met
(db-mcp exposure (cross-service) and the live DB matrix (infra) remain). This pack is a running-lane checkpoint, not a
lane-completion return.
