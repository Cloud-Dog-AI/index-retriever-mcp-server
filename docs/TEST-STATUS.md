---
template-id: T-TSS
template-version: 1.0
project: index-retriever-mcp-server
doc-last-updated: 2026-07-14T17:38:04Z
doc-git-commit: 3f4802369ad66d37b4c125033bc02dbc8c18b555
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-14T17:38:04Z
---

# index-retriever-mcp-server - TEST-STATUS

## 1. Latest run

- **Run timestamp:** NOT IMPORTED - no 2026-07-08..14 candidate satisfied every provenance field.
- **Commit:** `NOT IMPORTED` (`main` candidate review at `3f4802369ad66d37b4c125033bc02dbc8c18b555`)
- **Runtime:** N/A (no evidence-qualified run imported)
- **Lane:** `W28E-1863`, `W28E-1882`, and undispatched `W28R-3016` candidate review; not a run record.
- **Environment:** NOT RECORDED with a qualifying literal command and immutable result.
- **Command:** NOT RECORDED - no literal foreground invocation survives with all other provenance.
- **Evidence:** `docs/TEST-CANDIDATE-DISPOSITIONS-2026-07-08-14.md`.
- **Totals:** NOT IMPORTED; legacy/candidate outcomes below are excluded from canonical status.

## 2. Runtime truth

| Runtime | State | Preserved candidate truth |
|---|---|---|
| CPython 3.12 | **NOT IMPORTED** | W28E-1863 claims 421 passed node IDs plus 5 conditional skips, but no literal command/environment evidence tuple is retained. W28R-3016 was not run. |
| CPython 3.13 | **NOT RUN** | W28R-3016 was not dispatched; no qualifying 3.13 run exists. |
| N/A (Node/Playwright) | **NOT IMPORTED** | W28E-1882 evidence includes an 88/88 final candidate and earlier failure/skip runs, but lacks exact command transcript and corrected immutable tags. |

## 3. Per-test status

No per-test rows are imported from the review window.
