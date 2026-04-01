# Tests

## Service Scope
Ingestion, parser orchestration, OCR/table handling, indexing, search, retrieval, and queue-backed maintenance for enterprise content.

## Test Inventory
| Tier | Present | Notes |
|------|---------|-------|
| `quality` | Yes | Repository contains the `quality` test tier. |
| `unit` | Yes | Repository contains the `unit` test tier. |
| `system` | Yes | Repository contains the `system` test tier. |
| `integration` | Yes | Repository contains the `integration` test tier. |
| `application` | Yes | Repository contains the `application` test tier. |
| `contract` | Yes | Repository contains the `contract` test tier. |
| `parser` | Yes | Repository contains the `parser` test tier. |
| `security` | Yes | Repository contains the `security` test tier. |

## Current Evidence Model
- The repository keeps execution evidence in repo-local working reports and rerunnable pytest suites.
- Before release, rerun the relevant `QT`, `UT`, `ST`, `IT`, and `AT` tiers against the intended environment overlays.
- This document records the current catalogue rather than claiming a release verdict.

## Standard Commands
```bash
python3 -m pytest tests/quality --env tests/env-QT -q
python3 -m pytest tests/unit --env tests/env-UT -q
python3 -m pytest tests/system --env tests/env-ST -q
python3 -m pytest tests/integration --env tests/env-IT -q
python3 -m pytest tests/application --env tests/env-AT -q
```

## Notes
- Top-level test directories present: `__pycache__`, `application`, `contract`, `integration`, `parser`, `quality`, `security`, `system`, `unit`.
- Environment overlays and private credentials are intentionally not published in this document set.

## W28A-513 Added Coverage

### ST1.15 E2E gap coverage
- File: `tests/system/ST1_15/test_st1_15_e2e_gap_coverage.py`
- Purpose:
  - verify all documented chunking strategies against a real VDB-backed ingest path,
  - verify a real OCR provider path (`local` / Tesseract),
  - verify the actual retrieval output contract (inline content plus source URI traceability).
- Requirements covered:
  - `FR-09A`
  - `FR-10A`
  - `FR-14A`

### UT1.40 tool registry completeness
- File: `tests/unit/UT1_40/test_ut1_40_tool_registry.py`
- Purpose:
  - enforce the exact runtime tool inventory count (`60`),
  - ensure names are unique and the registry contract remains stable.
- Requirements covered:
  - `FR-16A`
