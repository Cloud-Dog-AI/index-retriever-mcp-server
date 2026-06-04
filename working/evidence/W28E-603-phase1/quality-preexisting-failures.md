# W28E-603 Phase 1 — Quality-tier failure triage (honest disclosure)

`pytest tests/quality --env tests/env-QT` ends with **2 failures**. Both are **pre-existing**, in files
this lane never touched, and fail identically on pristine `origin/main` (7157c13). This lane introduced
**zero** new quality-gate failures and fixed the one it did cause (RC-04).

## RC-04 — public docstring coverage (CAUSED BY THIS LANE → FIXED)
- First run after adding the structure code: `79.83% < 80.0%` — my new public functions lacked docstrings.
- Fix: added one-line docstrings to every flagged function (api_server structure handlers, repository &
  service read methods). Re-run: **RC-04 PASS** (quality tier 45 passed, was 44).

## RC-01 — no hardcoded URLs/loopback (PRE-EXISTING, not this lane)
- Violations (all in `src/index_server/web_server.py`, untouched by this lane):
  - `web_server.py:86 -> return "127.0.0.1"`
  - `web_server.py:87 -> return host or "127.0.0.1"`
  - `web_server.py:96/151/152 -> f"http://{...host}:{...port}"`
- `git diff --name-only origin/main` does NOT include `web_server.py`.
- **Pristine proof:** ran on a throwaway worktree off `origin/main` (HEAD 7157c13) with NO W28E-603 changes →
  `test_rc01_no_hardcoded_urls_or_loopback` FAILED with the identical web_server.py violations.

## RC-09 — no stub/placeholder markers (PRE-EXISTING, not this lane)
- Violation: `src/index_tools/connectors/resolver.py:103 -> raise NotImplementedError(` (untouched by this lane).
- `git diff --name-only origin/main` does NOT include `connectors/resolver.py`.
- **Pristine proof:** same throwaway `origin/main` worktree → `test_rc09_no_stub_placeholders` FAILED with the
  identical resolver.py violation.

## Conclusion
- New quality failures introduced by W28E-603 Phase 1: **0**.
- Pre-existing quality failures (out of this lane's scope, separate owners): **RC-01, RC-09**.
- These two are platform/IR debt that pre-dates this lane; flagged here for the coordinator, not silently
  absorbed. They are NOT document-structure related and changing `web_server.py` host handling or implementing
  the `resolver.py` connector is outside Phase 1 scope.
