# W28E-603 — Full pytest suite results (Phase 1 + Phases 2-5), live backends

Run with the sanctioned env-vault token sourced. Every Python tier is green; the one application-tier
non-pass is a known WebUI/Playwright flake (AT_WEBUI_CollectionCrud) that passes 2/2 in isolation and is
not touched by this lane (no collection/WebUI source changed).

| Tier | Command | Raw result |
|---|---|---|
| unit | pytest tests/unit --env tests/env-UT | 209 passed, 0 failed |
| quality | pytest tests/quality --env tests/env-QT | 47 passed, 0 failed |
| security | pytest tests/security --env tests/env-QT | 6 passed, 0 failed |
| parser | pytest tests/parser --env tests/env-PT | 3 passed, 0 failed |
| contract | pytest tests/contract --env tests/env-IT | 4 passed, 0 failed |
| integration | pytest tests/integration --env tests/env-IT | 54 passed, 0 failed |
| system | pytest tests/system --env tests/env-ST | 26 passed, 2 skipped |
| application | pytest tests/application --env tests/env-AT | 24 passed (AT_WEBUI_CollectionCrud flaked under full-suite load; passes 2/2 isolated) |

Phase 2-5 additions: unit UT_W28E603_Phase25 (9), integration IT_W28E603_Phase25 (3). §1.4 grep over the
new structure/extraction/corpus/template files: zero matches (cloud_dog_db + cloud_dog_vdb + stdlib only).
