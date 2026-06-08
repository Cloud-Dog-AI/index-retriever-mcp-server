# W28E-603 Phases 2–5 — Requirements (structure extraction, corpus, templates)

Closes design-brief §25 acceptance criteria #2, #3, #8, #9, #10 (and extends #6, #14) on top of the
Phase-1 foundation. Grounded in EXISTING code — no rebuilds:
- Parsers already implemented + tested: MinerU (`mineru`), Marker (`marker_mcp`), Docling (`docling`)
  via `cloud_dog_vdb` `build_parser_registry()` / `parse_bytes()` → IR with
  `full_text()/text_blocks/table_blocks/metadata/quality/provider_id/provider_version` (IT2_8/9/10).
- Durable jobs: `src/index_tools/queue/engine.py` `QueueEngine.enqueue/run/record_progress/register_handler`.
- Deterministic identity + provenance: `cloud_dog_vdb.metadata` (`compute_content_hash`, `merge_provenance`).
- Phase-1 canonical model + persistence + `StructureService` (create/get/list/delete/outline).

## FR-EXT — Structure extraction (providers) — §25 #2, #3
- FR-EXT-1: `StructureService.extract(...)` transforms parser IR → canonical `StructureBundle` and persists it
  (reuses the Phase-1 `create()` path, deterministic IDs, audit).
- FR-EXT-2: Provider interface represents MinerU, Marker, Docling through one normaliser with graceful
  capability flags; the always-available `internal` provider is the offline-deterministic default.
- FR-EXT-3: IR → canonical mapping: `text_blocks`→`StructureBlock`, `table_blocks`→`StructureTable`,
  page metadata→`StructurePage`, provider/version→`StructureExtractorRun` + `StructureDocument` provenance,
  `quality`→`quality_score`. Section inference from heading blocks.
- FR-EXT-4: Extraction runs as a durable job (`structure_extract` job_type) with progress checkpoints; a
  synchronous `extract_text` path exists for inline content + tests.
- FR-EXT-5: MCP tools `structure_extract`, `structure_extract_from_indexed_document`; API
  `POST /api/v1/structure/extract`. RBAC `collection.write`. Audited.

## FR-COR — Corpus management + analysis — §25 #8, #9
- FR-COR-1: `StructureCorpus` resource (named set of structure documents) — create/list/get/update/delete,
  persisted through `cloud_dog_db`.
- FR-COR-2: Corpus analysis is a durable job (`structure_corpus_analyse`) computing patterns across the
  corpus's documents: section patterns, style patterns, page/layout patterns, table patterns.
- FR-COR-3: `StructurePattern` records (pattern_type, signature, support/occurrence_count, examples,
  confidence) persisted and queryable.
- FR-COR-4: A corpus report aggregates the patterns (counts, distributions, dominant section/style classes).
- FR-COR-5: MCP `structure_corpus_create/list/get/update/delete/analyse/patterns_get`; API
  `/api/v1/structure/corpora*`. Analyse = `collection.write`; reads = `collection.read`. Audited.

## FR-TPL — Template intelligence — §25 #10
- FR-TPL-1: `StructureTemplate` blueprint generated from a corpus's patterns: ordered section blueprint,
  per-section block-type signature, style guide (dominant normalised styles), with provenance to the corpus.
- FR-TPL-2: Export a template as Markdown and as JSON (`structure_template_export`).
- FR-TPL-3: MCP `structure_template_generate/get/list/export`; API `/api/v1/structure/templates*`.
  Generate = `collection.write`; read/export = `collection.read`. Audited.

## NFR — platform-standards alignment (RULES §1.4 / §6.88)
- Persistence only through `cloud_dog_db` (SQL + JSON; new tables via the existing Alembic mechanism).
- Long-running work only through the existing `QueueEngine` (no bespoke threads/executors for jobs).
- Identity/provenance through `cloud_dog_vdb.metadata` helpers; parsing through `cloud_dog_vdb` registry.
- Transport-neutral service layer; API/MCP route into one `StructureService`.
- Zero bespoke DB/HTTP/logging/cache clients; §1.4 grep must be zero over new files.

## Test requirements
- Offline-deterministic by default: extraction via the `internal` provider; corpus + template logic are
  pure computation over the persisted SQL store (no live backends).
- Unit: IR→bundle mapping, extraction round-trip, corpus pattern extraction, template generation + export.
- Integration: MCP tools/call + REST for extract/corpus/template (authenticated TestClient).
- Backend-matrix smoke continues (sqlite); existing 361-test suite remains green (regression).
