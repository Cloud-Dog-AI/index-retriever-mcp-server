---
template-id: T-SCM
template-version: 1.0
applies-to: tests/SCOPE-MAP.md
project: index-retriever-mcp-server
doc-last-updated: 2026-06-17T00:00:00Z
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-06-17T00:00:00Z
---

# index-retriever-mcp-server - Test scope map

## Mapping

| Source glob | QT | UT | ST | IT | AT |
|---|---|---|---|---|---|
| `src/**/*.py` | `tests/quality/**/test_*.py` | `tests/unit/**/test_*.py` | `tests/system/**/test_*.py` | `tests/integration/**/test_*.py` | `tests/application/**/test_*.py` |
| `docs/**/*.md` | `tests/quality/QT_COMPLIANCE/test_qt_traceability.py` | - | - | - | - |
| `scripts/**/*.py` | `tests/quality/**/test_*.py` | `tests/unit/**/test_*.py` | - | - | - |

## Cross-references

- Requirements catalogue: `docs/REQUIREMENTS.md`
- Test catalogue: `docs/TESTS.md`
- Coverage matrix: `docs/REQ-COVERAGE.md`
