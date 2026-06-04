# W28E-603 Phase 1 — Reading Proof (Current Assurance Addendum)

Lane: **W28E-603 — Index-Retriever Document Structure Intelligence**, Phase 1 (Model & Persistence Foundation).
Target repo: `index-retriever-mcp-server`. Worktree: `/opt/iac/Development/cloud-dog-ai/.w28e603-ir-wt`,
branch `w28e-603-phase1-structure` off `origin/main` @ `7157c13`.
Date: 2026-06-04. Background processes: **NO**.

## Mandatory files read

| # | File | Version / anchor |
|---|------|------------------|
| 1 | `cloud-dog-ai-platform-standards/RULES.md` | **v2.7** (2026-06-01) |
| 2 | `cloud-dog-ai-platform-standards/AGENT-LESSONS.md` | **v3.13** (2026-06-04) |
| 3 | `cloud-dog-ai-platform-standards/AGENT-BOOTSTRAP-DIRECTIVE.md` | read |
| 4 | `index-retriever-mcp-server/AGENT-LESSONS.md` | IR deltas (W28A-602/878/882/884/908a/908b/964); no numeric version line |
| 5 | Design brief `working/INDEX-RETRIEVER-MCP-AGENT-DESIGN-BRIEF-2026-05-27.md` | 1330 lines, read (§1–27) |
| 6 | `index-retriever-mcp-server/docs/ARCHITECTURE.md` | read |

## PRE-FLIGHT reading proof (instruction §PRE-FLIGHT)

1. **RULES.md §1.4 — name 3 platform packages:** `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_db`
   (full mandatory set also: `cloud_dog_cache`, `cloud_dog_storage`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_vdb`).
   §1.4 now folds `cloud_dog_db.nosql` (W28E-605) into the mandatory list; direct `pymongo`/`couchdb`/`elasticsearch`/`opensearchpy`/`cassandra-driver`
   use in service code is a §1.4 violation.
2. **AGENT-LESSONS §6.78 — rule about IR enhancements:** "New skeleton projects are planning-only; no runtime claims until
   code exists." It explicitly names *two index-retriever enhancements* as planning skeletons with ZERO runtime code/tests
   until code is written. ⇒ Phase 1 may not claim runtime behaviour without real code + passing tests.
3. **Design brief §3 — strategic design decision (VDB vs canonical store):** The canonical document structure MUST NOT be held
   only in a VDB. The VDB is a retrieval layer, not the source of truth. Canonical structure is persisted through `cloud_dog_db`
   (SQL backends may use JSON/JSONB + relational tables behind the common interface; document backends preserve the same model
   and API contracts). The VDB holds derived search views only.
4. **Design brief §22 — 3 implementation guardrails:** (a) Reuse existing platform packages by default; (b) Extend `cloud_dog_db`
   for document-DB support rather than bypassing it; (c) Do not put canonical document structure only in the VDB / do not add
   one-off local DB clients / keep API, MCP, A2A and WebUI routed into common service-layer operations.
5. **RULES.md version:** 2.7
6. **AGENT-LESSONS version:** 3.13 (platform)

## Lane dependency status

- **Gate W28A-352D (index-retriever WebUI conformance) — CLEARED.** Raw: `working/w28a-352d/conformance-r2-final.log` → `1 passed`;
  `working/w28a-352d/conformance-r2-result-9of9.json` → every check `PASS`.
- **§3 foundation dependency — UNBLOCKED.** `cloud_dog_db` **v0.3.0** ships a real `cloud_dog_db.nosql` surface
  (`document.py`/`search.py`/`vector.py`/`timeseries.py`/`widecolumn.py`/`connectors/`). Phase 1 uses the canonical **SQL surface**
  (`PlatformBase`+`TimestampMixin`, Alembic, `SyncSessionManager`) with JSON columns — explicitly permitted by §3 and matching the
  existing validated in-repo pattern (`src/index_tools/db/`). The `nosql.document` surface adoption is a later phase.

## Lane credential / source boundary

- **LOCAL ONLY.** No preprod, no Docker push, no SSH, no deploy (instruction Hard Guards).
- **No Vault writes** of any kind. No Vault reads required for Phase 1 (sqlite default; postgres/mysql matrix legs skip when unconfigured).
- GitLab `origin` (`git.cloud-dog.net`) is the canonical internal source — `fetch`/`pull` used; **push deferred pending explicit user confirmation**.
- Tests run from the worktree using the existing `.venv` (Python 3.12.13) with `PYTHONPATH=<worktree>/src`, so `index_tools`/`index_server`
  resolve to the worktree while `cloud_dog_db` resolves to the installed package (verified).

## Final validator pass string (target)

`FINAL_EVIDENCE_VALIDATOR: PASS failures=0`
