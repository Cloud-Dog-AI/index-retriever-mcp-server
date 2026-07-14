---
template-id: T-TSS
template-version: 1.0
project: index-retriever
doc-last-updated: 2026-07-14T10:00:14.382Z
doc-git-commit: 2dd688bb4bb7b4504d752168736cfc575495c1ec
doc-git-branch: main
doc-age-policy: 30d
doc-conformance-stamp: 2026-07-14T10:00:14.382Z
---

# index-retriever — TEST-STATUS

> **Template version:** T-TSS v1.0 — overwritten by `scripts/update-test-state.py`. Do not hand-edit.

## 1. Latest run

- **Run timestamp:** 2026-07-14T10:00:14.382Z
- **Commit:** `2dd688bb4bb7b4504d752168736cfc575495c1ec` (`main`)
- **Runtime:** N/A (Node/Playwright)
- **Lane:** `W28E-1882`
- **Environment:** `deployed preprod; approved runtime/Vault credentials; service E2E_BASE_URL`
- **Command:** `bash /opt/iac/Development/cloud-dog-ai/tmp/W28E-1882/run-index-retriever.sh FINAL`
- **Evidence:** `W28E-1882-FINAL-PROOF-R2:working/evidence/W28E-1882/current/raw/index-retriever/index-retriever.FINAL.junit.xml`
- **Totals:** 88 tests | 88 passed | 0 failed | 0 errors | 0 skipped

## 2. Per-test status

| Test ID | Tier | Status | Last run | Commit | Known issue |
|---|---|---|---|---|---|
| `a11y.spec.ts::@a11y dashboard has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `a11y.spec.ts::@a11y ingest-search has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `a11y.spec.ts::@a11y structure documents has no wcag2aa violations` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/W28A-157-webui-compliance.spec.ts::dashboard uses API audit activity and human uptime` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/W28A-157-webui-compliance.spec.ts::ingest and retention pages expose profile and collection selectors` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/W28A-157-webui-compliance.spec.ts::observability uses selected limit and renders NIST audit columns` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/audit-job-health-observability.spec.ts::observability view loads backend, embedding, queue and jobs` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/collection-crud.spec.ts::create, list, and delete collection` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/collection-edit.spec.ts::load and update collection metadata` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/dedupe-and-reindex.spec.ts::duplicate ingest reuses same job id and reindex can be triggered` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X1 admin login` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X10 ingest text` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X11 search` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X12 file upload` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X13 retention page` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X14 MCP console` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X15 observability` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X2 dashboard verification` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X3 profile CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X4 user CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X5 group CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X6 API key CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X7 RBAC bindings` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X8 collection CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/forensic-webui.spec.ts::X9 source config CRUD` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/health-auth.spec.ts::health and auth readiness` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/health-auth.spec.ts::invalid API key stays on sign-in and reports auth failure` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/mcp-catalogue-and-tool-call.spec.ts::tool catalogue is visible and tool call executes` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/multi-backend-profile-switch.spec.ts::switching profile context preserves successful ingest/search workflow` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-002 health and version return 200` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-003 runtime-config + main assets + index load without 404/500` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-004 login page renders the shared login form (no blank/pageerror)` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-005 login alias /ui/login resolves without 404/5xx` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-006 bad credentials fail visibly without crashing` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-007 valid login materialises the principal via /auth/me` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-008 authenticated shell renders top bar, nav and account menu` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-009 canonical common pages render via hard navigation (no blank/pageerror)` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-010 service pages render via hard navigation — the crash-class guard` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-011 anonymous + wrong-target access does not leak protected content` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-012 browser cleanliness across the full journey` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/preprod-deploy-smoke.spec.ts::PS-PREPROD-DEPLOY-SMOKE: index-retriever-mcp-server target-service smoke › PDS-013 logout returns to the login gate` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/profile-crud.spec.ts::create, update, and delete runtime profile` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/profile-crud.spec.ts::reader token is denied profile mutation` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/retention-and-delete-controls.spec.ts::retention and delete controls require confirmation and execute` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/security-admin.spec.ts::user, group, api key, rbac, and config event administration` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/source-config.spec.ts::create, update, use, and delete source config` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/structure-corpora.spec.ts::create, analyse, and delete a structure corpus` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/structure-documents.spec.ts::extract, view, and delete a structure document` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/structure-templates.spec.ts::generate a template from a corpus, match a document, and delete` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P1 resource metrics show real data` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P10 session timeout shows countdown when authenticated` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P11 relative time appears on profiles list` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P12 admin pages are present and consistent` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P13 jobs page renders standard job columns` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P14 dashboard layout shows health, metrics, and quick actions` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P15 column picker persists hidden column state` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P16 no raw JSON blocks on dashboard, mcp console, and settings` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P2 log compliance returns non-empty messages` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P3 startup warnings are zero` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P4 page jump exists and changes page` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P5 sort arrows render on sortable table headers` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P6 multi-select shows bulk toolbar` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P7 API docs page loads` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P8 entity dialog opens and closes` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/ui-review2.spec.ts::P9 session timeout does not show on login page` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/upload-index-search.spec.ts::upload file, search indexed results, and retrieve` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-460-ui-adoption.spec.ts::W28A-460 local UI adoption verification` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-693-jobs-conformance.spec.ts::W28A-693 PS-76 v2 Jobs page conformance` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-775-ps72-console.spec.ts::W28A-775 PS-72 console conformance › T.1 MCP and A2A layout contract` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-775-ps72-console.spec.ts::W28A-775 PS-72 console conformance › T.2.1 and T.2.2 safe sync MCP/A2A calls populate result metadata` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-775-ps72-console.spec.ts::W28A-775 PS-72 console conformance › T.2.3 async bulk_index returns a Job ID and Jobs link` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-775-ps72-console.spec.ts::W28A-775 PS-72 console conformance › T.2.4 RBAC denial surfaces inline for unbound writer action` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-775-ps72-console.spec.ts::W28A-775 PS-72 console conformance › T.2.5 admin override succeeds for MCP and A2A` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.1 page load renders PS-81 explorer with no API/auth 4xx responses` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.2 ALL tab rendered key count matches generated inventory exactly` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.3 deterministic key sample has visible key, source badge, and expected value or mask` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.4 secret values are masked by default and reveal action records AU-3 audit text` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.5 page search highlights matching keys and clears back to the full tree` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.6 PS-81 expand collapse and copy controls are wired through the shared widget` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-805/settings/settings-compliance.spec.ts::W28A-805 Settings WebUI compliance › 3.7 server tabs exist, are non-empty, and expose scoped config only` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908a-rbac-negative.spec.ts::full ingest coverage, metadata filters, explain, and multi-collection search` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908a-rbac-negative.spec.ts::viewer sees collections read-only and collection create is denied` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908a-rbac-negative.spec.ts::writer sees source config mutations blocked but sync remains available across connector types` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908b-lifecycle-deploy.spec.ts::W28A-908b MCP console parser, preview, OCR, table extraction, and RBAC checks` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908b-lifecycle-deploy.spec.ts::W28A-908b jobs, retry, cancel, and surface log coverage` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a-908b-lifecycle-deploy.spec.ts::W28A-908b lifecycle, parity, metadata, dashboard, and observability coverage` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a734r2-idam-5page.spec.ts::all 5 PS-71 /idam/* pages render for an authenticated admin` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |
| `e2e/w28a734r2-negative-auth.spec.ts::clean-context unauth visitor is gated to login; /auth/me denies (NOT admin)` | UNCLASSIFIED | pass | 2026-07-14 | `2dd688bb` | |

## 3. Failures (detail)

_None._
