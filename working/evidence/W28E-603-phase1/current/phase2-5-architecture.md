# W28E-603 Phases 2–5 — Architecture

Builds on Phase 1 (`src/index_tools/structure/` + `db/structure_models.py`). Reuses existing parsers,
`QueueEngine`, and `cloud_dog_vdb`. New code is additive and transport-neutral.

## New modules (in `src/index_tools/structure/`)
```
providers.py   # provider registry + IR->StructureBundle normalisers (mineru/marker/docling/internal)
extract.py     # StructureExtractor: parse via cloud_dog_vdb -> normalise -> StructureBundle
corpus.py      # CorpusService: corpus CRUD + pattern analysis over persisted structure documents
templates.py   # TemplateService: blueprint generation from corpus patterns + Markdown/JSON export
```
Model additions in `models.py`: `StructureCorpus`, `StructurePattern`, `StructureTemplate`,
`TemplateExport`, plus enums `PatternType`. ORM additions in `db/structure_models.py`:
`structure_corpora`, `structure_corpus_members`, `structure_patterns`, `structure_templates`
(PlatformBase + TimestampMixin + JSON payload). Alembic migration `20260604_0003_structure_corpus_templates`.

## Extraction flow (§25 #2/#3)
```
extract(source_bytes|text, profile, collection, provider) 
  -> providers.parse(...)            # cloud_dog_vdb build_parser_registry + parse_bytes (or internal)
  -> normalise IR -> StructureBundle # text_blocks->blocks, table_blocks->tables, page meta->pages,
                                     #   heading blocks->sections, provider->ExtractorRun + provenance
  -> StructureService.create(bundle) # Phase-1 persistence + deterministic IDs + audit
```
Durable path: `QueueEngine` job_type `structure_extract`; handler calls the same extractor and records
progress (parse/normalise/persist). Sync `extract_text(...)` for inline content + offline tests
(provider=`internal`, always available — no live backend).

## Corpus flow (§25 #8/#9)
```
corpus_create(name, profile, collection, document_ids) -> StructureCorpus (cloud_dog_db)
corpus_analyse(corpus_id) [durable job structure_corpus_analyse]
  -> load member StructureBundles via repository
  -> compute patterns:
       section pattern  : normalised section-type sequence + level signature, support count
       style pattern    : dominant style_class/role/font signatures, observed_count
       layout/page      : page geometry + zone signatures
       table pattern    : row/col/header shape signatures
  -> persist StructurePattern rows + a corpus report (counts/distributions)
```
Pure computation over the SQL store — deterministic, offline-testable. No bespoke clustering libs;
signatures are deterministic tuples hashed via the Phase-1 `ids` helper.

## Template flow (§25 #10)
```
template_generate(corpus_id) 
  -> read top StructurePatterns for the corpus
  -> assemble StructureTemplate: ordered section blueprint + per-section block-type signature
     + style guide (dominant normalised styles) + provenance(corpus_id, pattern_ids)
  -> persist structure_templates row
template_export(template_id, format=markdown|json) -> rendered artefact (str)
```

## Transport wiring (matches Phase-1 recipe)
- `tools/registry.py`: add §13 ToolSpecs (structure_extract, structure_extract_from_indexed_document,
  structure_corpus_create/list/get/update/delete/analyse, structure_corpus_patterns_get,
  structure_template_generate/get/list/export).
- `mcp_server.py`: permission rows (read vs write) + execute_tool dispatch -> `service.structure.*`.
- `api_server.py`: nested handlers + routes `/api/v1/structure/{extract,corpora,templates}*`.
- `IndexService`: lazily expose `corpus`/`templates` via `structure` (or sibling properties); register
  queue handlers for `structure_extract` + `structure_corpus_analyse` in `__init__`.

## Platform alignment (RULES §1.4)
cloud_dog_db (persistence/migrations) · cloud_dog_vdb (parsing/metadata/identity) · QueueEngine (jobs) ·
cloud_dog_logging audit via existing AuditLogger · cloud_dog_config for any config. No bespoke replacements.
