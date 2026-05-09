# W28A-95a-R1 Index Retriever VDB Breadth Result

Date: 2026-05-09

## Runtime Guard

- `working/ps100-python-runtime-guard.log`
- `python=3.12.13`
- `asyncio_cross_thread=pass`
- `runtime_guard=pass`

## Standard Verification

- `working/w28a-95a-r1-it.log`: 46 passed in 346.18s
- `working/w28a-95a-r1-at.log`: 24 passed in 595.27s
- `working/w28a-95a-r1-qt.log`: 47 passed in 2.25s
- `working/w28a-95a-r1-parser-depth.log`: 70 passed in 904.78s

## VDB Matrix

- `working/w28a-95a-r1-env-VDB-chroma.log`: 70 passed in 892.69s
- `working/w28a-95a-r1-env-VDB-qdrant.log`: 70 passed in 852.48s
- `working/w28a-95a-r1-env-VDB-pgvector.log`: 70 passed in 862.19s
- `working/w28a-95a-r1-env-VDB-weaviate.log`: 70 passed in 926.90s
- `working/w28a-95a-r1-env-VDB-infinity.log`: 70 passed in 891.78s
- `working/w28a-95a-r1-env-VDB-opensearch.log`: 70 passed in 897.04s

## Additional Evidence

- `working/w28a-95a-r1-vault-resolution.log`: all VDB env files resolved without literal `${vault...}` placeholders.
- `git diff --check`: pass.

## Result

Accepted gate evidence is green under `.venv/bin/python` CPython 3.12.13. No skips or xfails were added.
