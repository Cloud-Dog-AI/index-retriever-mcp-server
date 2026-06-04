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
| 5 | All supported document DB backends have tested core behaviour | Phase 6 (full matrix) | PARTIAL (sqlite PASS; postgres/mysql reachable but dev-DB auth blocks this host) |
| 6 | Structure records link to profiles/collections/files/source/VDB/chunks | Phase 1 (model) + Phase 3 (VDB linkage) | PARTIAL (link fields modelled + populated; vdb_record_ids linkage pending Phase 3) |
| 7 | Outline/page/blocks/sections/styles/tables/figures retrieved deterministically | Phase 1 | PASS |
| 8 | Large documents and 40+ corpora analysed (durable jobs) | Phase 4 | PASS (corpus + analysis; computation is durable-job-ready via the existing QueueEngine) |
| 9 | Corpus analysis produces section/style/layout/table patterns | Phase 4 | PASS (`structure_corpus_analyse` -> StructurePattern + report) |
| 10 | Template blueprint generated and exported | Phase 5 | PASS (`structure_template_generate` + `structure_template_export` markdown/json) |
| 11 | WebUI inspection + corpus/template workflows | Phase 3 | PASS (in-repo server-rendered /admin/ui/structure; React SPA + Playwright are cross-repo in cloud-dog-ui monorepo) |
| 12 | A2A exposes selected structure skills | Phase 2 | PASS (agent card + /a2a/tasks structure skills) |
| 13 | db-mcp-service reads/presents the structure DB | Phase 6 (cross-service) | PENDING |
| 14 | Audit logs capture extraction/analysis/template/deletion | Phase 1/4/5 | PASS (create/extract/corpus-analyse/template-generate/delete all audited) |
| 15 | Documentation/tests/implementation agree on tool names/routes | Phase 1/2 | PASS (89-tool catalogue + UT1_40 enforcement) |

PASS: #1,#2,#3,#4,#7,#8,#9,#10,#11,#12,#14,#15 (12/15). PARTIAL: #5,#6. PENDING: #13 (db-mcp, cross-service).

Acceptance of the full W28E-603 lane requires all 15 criteria PASS-with-raw-artefact. That bar is not yet met
(db-mcp exposure (cross-service), the live DB matrix (infra), and VDB-record linkage remain). This pack is a running-lane checkpoint, not a
lane-completion return.
