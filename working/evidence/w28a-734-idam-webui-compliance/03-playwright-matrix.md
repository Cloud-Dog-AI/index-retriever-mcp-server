# W28A-734 — 03 Playwright Conformance Matrix

Live run (existing-server mode; backend + UI both from this lane's worktrees):
`playwright-conformance.log` — **8 passed (27.8s)**, deterministic across two runs.

Command:
`E2E_USE_EXISTING_SERVER=1 E2E_BASE_URL=http://127.0.0.1:5197 npx playwright test tests/e2e/w28a-734-idam-webui-conformance.spec.ts --trace=on --workers=1`

## Evidence Matrix

| Requirement | Raw artefact | Raw value observed | Verification command | Pass |
|-------------|--------------|--------------------|----------------------|------|
| Users route + seed admin + exact columns + DataTable surface + buttons (Steps 1.1/2/4/6) | 05-traces/trace-820cf-...zip, 04-screenshots/users.png, playwright-conformance.log | headers `username,display_name,role,groups,enabled,last_login,created`; admin row + admin badge; footer `Total Records: N • Page X of Y`; `+ Add User`/`Bulk Delete` | npx playwright test ...conformance.spec.ts:44 | PASS |
| Groups route + seeded groups + exact columns + button (Steps 1.2/4/6) | 05-traces/trace-d7a5b-...zip, 04-screenshots/groups.png | headers `name,description,member_count,rbac_binding_count`; `administrators`+`ragflow` rows; `+ Add Group` | npx playwright test ...conformance.spec.ts:78 | PASS |
| API Keys exact columns + Generate flow + reveal-once + owner populated + no secret in DOM (Steps 1.3/4/7.3) | 04-screenshots/api-keys.png, playwright-conformance.log | headers `label,owner,scope_summary,created,expires,last_used,status`; reveal modal "This key will not be shown again." + Copy/Download/Acknowledge; owner non-empty; secret absent post-close | npx playwright test ...conformance.spec.ts:95 | PASS |
| RBAC exact columns + default admin binding + per-user/per-group views (Steps 1.4/4) | 05-traces/trace-99c02-...zip, 04-screenshots/rbac.png | headers `subject,resource,permission,granted_by,granted_at`; `user:admin` binding; Flat/By User/By Group selectable | npx playwright test ...conformance.spec.ts:135 | PASS |
| Edit is a modal sub-dialog with Cancel/Delete/Save; Escape closes (Step 3) | 05-traces/trace-4d5e0-...zip, 04-screenshots/users-edit-dialog.png | dialog with Cancel + Delete + Save; Escape hides dialog | npx playwright test ...conformance.spec.ts:157 | PASS |
| CRUD create via WebUI persists across reload (Step 7.1) | 05-traces/trace-6185a-...zip | created user row present after reload (backend-durable) | npx playwright test ...conformance.spec.ts:177 | PASS |
| Multi-select Bulk Delete removes selected rows (Step 7.4) | 05-traces/trace-6fd08-...zip | two selected rows removed after confirm | npx playwright test ...conformance.spec.ts:198 | PASS |
| Low-privilege RBAC denial: inline/hidden, no JS exception (Step 7.2) | 05-traces/trace-cebda-...zip | reader denied admin IDAM access; zero page JS errors | npx playwright test ...conformance.spec.ts:231 | PASS |

PC3 exact summary line (per shard): `8 passed (27.8s)` (single chromium project, workers=1).
PC17: assertions use exact `toEqual` header arrays and `{ exact: true }` name matches; no `.or()` acceptance.
PC27: foreground execution. PC29: artefacts under `working/`. PC32: backend + preview stopped, all ports free.
