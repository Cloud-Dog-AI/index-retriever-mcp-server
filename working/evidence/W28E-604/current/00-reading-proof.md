# W28E-604 — 00 Reading Proof + PRE-FLIGHT

Lane: **W28E-604 — Index-Retriever Excel/Spreadsheet Indexing**
Date: 2026-06-04
Role: Auditor/builder (full 3-phase build, user-authorised)

## Mandatory files read

| # | File | Version / proof |
|---|------|-----------------|
| 1 | `cloud-dog-ai-platform-standards/RULES.md` | **Version 2.7** |
| 2 | `cloud-dog-ai-platform-standards/AGENT-LESSONS.md` | **Version 3.13 — 2026-06-04** |
| 3 | `cloud-dog-ai-platform-standards/AGENT-BOOTSTRAP-DIRECTIVE.md` | read |
| 4 | `index-retriever-mcp-server/AGENT-LESSONS.md` | read (py3.12; ports 5197/18686; AT2_5 long; clear runtime-config cache in fixtures) |
| 5 | `index-retriever-mcp-server/working/VDB-INDEX-RETRIEVER_EXCEL_REQUIREMNTS_260527.md` | 1236 lines read in full (§1–§24) |
| 6 | `cloud-dog-ai-platform-standards/packages/backend/platform-vdb/` (cloud_dog_vdb source) | mapped: VDBClient/Record/CollectionSpec/SearchRequest; adapters chroma/qdrant/weaviate/opensearch/pgvector/infinity; v0.5.4 |

## READING PROOF (PRE-FLIGHT answers)

1. **RULES.md §1.4 — name 3 platform packages:** `cloud_dog_config` (config/Vault/env precedence), `cloud_dog_vdb` (vector DB abstraction + embeddings), `cloud_dog_db` (DB abstraction, migrations, NoSQL/search/pgvector — `cloud_dog_db.nosql`, W28E-605). (Full set is 10: + `cloud_dog_logging`, `cloud_dog_cache`, `cloud_dog_storage`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_llm`.) Bespoke replacement of any is a VIOLATION.

2. **AGENT-LESSONS §6.78 — rule about IR enhancements:** New skeleton projects (incl. the two index-retriever enhancements: doc-structure + Excel-indexing) are **planning-only**; no runtime claims until code exists. Binding rules: (3) **LOCAL ONLY** until coordinator authorises preprod; (4) **100% platform package reuse** from day one (all 10 backend packages); (6) **MUST NOT break existing VDB indexing/search/retrieve**.

3. **Excel requirements §4 — high-level architectural principles (3):** (1) Treat Excel as **semi-structured data, not a flat document**; (2) **Normalise once, index many** — canonical model before backend indexing; (3) **Index at multiple granularities** (workbook/sheet/table/column/row-batch/pivot/formula). (Plus: hybrid retrieval; preserve provenance; separate control plane from retrieval plane.)

4. **Excel requirements §22 — key design decisions (3):** (1) Excel indexed as **multiple object types, not one document**; (2) **SQL metadata persistence required** and must support SQLite/MariaDB/PostgreSQL; (3) a **canonical intermediate model is mandatory** to decouple parsing from backend indexing. (Plus: formal + inferred tables first-class; row-level controlled/batched; pluggable backends; ODS first-class; structured extraction queries part of the contract; object-aware refresh.)

5. **RULES.md version:** 2.7

6. **AGENT-LESSONS version:** 3.13 (2026-06-04)

## Lane dependency status

- **Gate W28A-352D (index-retriever conformance)** — **ACCEPTED** (archive CONTEXT-SUMMARY-W28A-355: "W28A-352D is ACCEPTED. IR enhancements (W28E-603/604) are unblocked."). Gate cleared.
- W28E-604 not yet in active dispatch table; no prior branch/tag/evidence. Fresh lane.
- Sibling W28E-603 (doc-structure, same gate/repo) also undispatched.

## Credential / source boundary

- **LOCAL ONLY.** No preprod, no Docker push, no SSH, no GitHub/GHCR/pypi.org push (RULES §6.78.3; hard guards).
- **No Vault writes** (binding). Internal PyPI `pypi.cloud-dog.net` = 401 (auth-gated); not needed — work is local-source editable installs.
- Isolated git worktrees off `origin/main` (per isolated-worktree-per-lane lesson), because both main checkouts were sitting on other lanes' branches (IR: fix/W28A-861; mono: w28d-317) with uncommitted work — must not contaminate.

## Architecture decision (§1.4-driven)

Excel canonical extraction is a genuine platform gap (no platform package provides it). §1.4 mandates **extending the platform package, not adding bespoke code to the service**. Therefore:
- **`cloud_dog_vdb/spreadsheet/`** (NEW, pure-functional, reusable): parse → canonical model → searchable `Record` list + object manifest. Reuses cloud_dog_vdb's existing 5 backend adapters (does NOT re-implement them — re-implementing adapters would be the §6.78/W28A-958 incident).
- **IR service** owns the §14 SQL control plane via `cloud_dog_db` (matches existing `db/models.py` + `database/migrations/cloud_dog_db/` precedent) and wires the pure pipeline into ingest. Separation of control plane (SQL) from retrieval plane (VDB) per §4.6.

## Worktrees + baseline

- IR worktree: `working/w28e604-ir-wt` @ branch `w28e604-excel` (origin/main 7157c13).
- Mono worktree: `working/w28e604-vdb-wt` @ branch `w28e604-vdb-excel` (origin/main 212bb277).
- **Regression baseline — platform-vdb UT: `109 passed`** (`.venv/bin/pytest tests/unit --env tests/env-UT -q`, py3.10, after `pip install asyncpg`). IR baseline captured at Phase 1b.

## Background processes: NO
