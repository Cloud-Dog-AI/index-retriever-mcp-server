# W28E-603 — Full pytest suite results (every tier), live backends

Run with the sanctioned `env-vault` token sourced so live VDB / IDAM / embedding backends resolve.
Every Python tier passes. The two skipped legs are the structure backend-matrix postgresql/mysql legs:
they skip because the dev database rejects credentials from this client host (an infrastructure boundary,
captured as raw evidence in `quality-and-rbac-fixes.md`); the connection path itself reaches the live
servers correctly.

| Tier | Command | Raw result |
|---|---|---|
| unit | pytest tests/unit --env tests/env-UT | 200 passed, 0 failed |
| quality | pytest tests/quality --env tests/env-QT | 47 passed, 0 failed |
| security | pytest tests/security --env tests/env-QT | 6 passed, 0 failed |
| parser | pytest tests/parser --env tests/env-PT | 3 passed, 0 failed |
| contract | pytest tests/contract --env tests/env-IT | 4 passed, 0 failed |
| integration | pytest tests/integration --env tests/env-IT | 51 passed, 0 failed |
| system | pytest tests/system --env tests/env-ST | 26 passed, 2 skipped |
| application | pytest tests/application --env tests/env-AT | 24 passed, 0 failed |

Total: 361 passed, 0 failed, 2 skipped (matrix postgres/mysql legs — infrastructure credential boundary).

Raw tier logs: `test-unit-regression-full.log`, `test-quality-full.log`, `test-integration-transports.log`,
`test-system-matrix.log`, `test-unit-structure.log`.
