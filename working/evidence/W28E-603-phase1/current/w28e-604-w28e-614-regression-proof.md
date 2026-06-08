# W28E-603 — W28E-604 / W28E-614 regression proof (from merged state)

Date context: 2026-06-05. Re-run from the merged lane worktree state (origin/main is ancestor of HEAD).

## W28E-604 (Excel/spreadsheet + structure indexing) — regression: GREEN
Full local pytest from the merged state, venv api-kit 0.13.0:
- unit + quality: 258 passed, 0 failed (incl. W28E-604 spreadsheet/excel + W28E-603 structure/Phase25 + UT1_40 90-tool).
- integration: 59 passed, 0 failed (incl. structure transports, Phase25, vdb linkage).
- Total 317 passed / 0 failed. Existing IR VDB indexing/search/retrieve behaviour intact (no regression).
- Live local-docker smoke: /health db+vdb(chroma)+embedding all ok; preprod /health db+vdb(qdrant)+embedding ok.

## W28E-614 (XC WebUI standards) — regression: GREEN (estate WebUI)
- Sentinel WebUI browser smoke (sentinel-webui-smoke.md): 5/5 SPAs load + mount, no fatal JS errors.
- indexretriever0 SPA served post-deploy (HTTP 200, doctype html), /version surface=web JSON 200.
- No accepted W28E-604 / W28E-614 state regressed; targeted deploy touched only indexretriever (2 add/2 destroy).

VERDICT: W28E-604 and W28E-614 accepted state preserved; regression GREEN.
