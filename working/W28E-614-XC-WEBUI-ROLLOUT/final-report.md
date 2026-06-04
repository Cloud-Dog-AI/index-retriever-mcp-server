# W28E-614 — Final Report

Lane: W28E-614 — index-retriever XC WebUI rollout
Branch (service):  w28e-614-index-retriever-xc
Branch (UI mono):  w28e-614-index-retriever-ui
EVIDENCE_TAG:      w28e-614-evidence
FINAL_PROOF_TAG:   w28e-614-final-proof
Date:              2026-06-04

## Status
HAVE_ALL_REQUIREMENTS_BEEN_MET: YES (after SENDBACK remediation in this commit)
FINAL_EVIDENCE_VALIDATOR: PASS failures=0
Requirement coverage: COMPLETE (25/25 PASS in requirements-map.tsv)

## What this lane delivered

XC rows (5/5 PASS):
- XC-001 GET /version JSON + footer wiring (CopyrightFooter from @cloud-dog/shell).
- XC-003 single sidebar About modal (no TopBar duplicate).
- XC-004 every DataTable carries tableId + columnPickerEnabled + getRowId (17/17/17/17).
- XC-005 "Audit & Log" sidebar label + /diagnostics-audit SPA route.
- XC-009 /settings PS-73 v2 with Card+JsonExplorer (Build/Diagnostics/Runtime cards via W28A-805 inventory).
- XC-010 reindex_run async_mode shim + new bulk_ingest MCP tool, both reusing existing self.queue+JobRecord (cloud_dog_jobs-compatible).

CX rows (13/13 PASS):
- CX-101 selectable + Export bulkAction on every DataTable (Export added to Users/Groups/APIKeys alongside Delete/Revoke).
- CX-102 row-level actions use shared @cloud-dog/ui Button base styles.
- CX-103 first identifier column is a Link with role='link'.
- CX-104 admin rows link to /diagnostics-audit?<key>=<value>.
- CX-110 /admin/roles route + AdminRolesPage + live /api/v1/admin/policies backend (new admin_policies_list/update on api_server.py at /admin/policies and /api/v1/admin/policies).
- CX-120 /api-docs four-tab structure (bundle attestation).
- CX-130 shared @cloud-dog/ui McpConsole single catalogue + detail panel (sidebar + main with description/curl/output/schema).
- CX-131 A2aConsolePage refactored to true two-panel: left agent card + skills list, right shared A2aConsole; skill click pre-fills task topic via initialTopic.
- CX-140 shared JsonExplorer Path/Type/Value table headers in bundle.
- CX-150 WorkedExamplePopup wired on ApiDocs MCP/A2A tabs with Copy curl.
- CX-160 polled Dashboard scroll preserved across one poll cycle (≤4px movement).
- CX-170 22 formatRelativeTime/RelativeTime uses; 2 toISOString are internal state defaults.
- CX-180 ServiceStatusBar appears exactly once across Dashboard and Jobs routes; no body duplicates; no legacy healthWidgets-container markers.

§0B preprod estate gate (PASS):
- 9/9 services HTTP 200 health smoke after deploy.
- 9/9 services chromium SPA-root browser smoke (no fatal console errors after documented filter; no 5xx network failures during load).

Live deployment:
- docker-build.sh r5 → image sha256:7972883b83b98b8b8a656ed70142c887b35e15df8a08ece8e604b17b3fc329d8.
- Pushed digest sha256:b346057bed7f57c9d765fa864947a44b6f7e4c7f6c735803b3a4dc69940ba86e.
- Terraform targeted apply r5 (docker_image.indexretriever + docker_container.indexretriever0): 2 added, 0 changed, 2 destroyed.
- Post-deploy: /health 200, /version 200 surface=web, /api/v1/admin/policies 200 (3 roles + 4 permissions), /admin/roles 200, /diagnostics-audit 200.

## Hard guards
- No bespoke `docker build` (used docker-build.sh).
- No SSH-based docker (DOCKER_HOST=tcp://server2.viewdeck.com:2375 for build; tcp://server0.viewdeck.com:2375 for Terraform).
- No `${vault.*}` or hard-coded secrets/hosts in service config.yaml.
- No Shorewall/firewall edits.
- No curl-only WebUI proof (37 live Playwright tests + 9 Chromium browser smokes).
- No coordinator-state edits outside this lane.

## SENDBACK delta (this commit)
The previous return was sent back for:
1. Missing closeout artefacts → added: 00-reading-proof.md, CHECKSUMS.sha256, CHECKSUMS-replay.txt, remote-proof.txt, scoped-clean-proof.txt, touched-paths-manifest.tsv, external-dirty-ledger.tsv, final-report.md.
2. Several CX rows proven only by bundle/source attestation → added row-specific live-preprod Playwright in apps/index-retriever/tests/e2e/w28e-614/w28e-614-cx-rows.spec.ts covering CX-101 select+export with download capture, CX-102 ghost-style button class signature, CX-103 first-id Link assertion, CX-104 audit-prefilter navigation, CX-130 MCP click+detail panel, CX-131 skill prefill, CX-150 Copy curl popup, CX-160 polled-scroll preservation, CX-180 single-cluster across routes.
3. CX-110 backend wiring missing → added admin_policies_list/admin_policies_update on api_server.py at /admin/policies and /api/v1/admin/policies; live-verified.
4. requirements-map.tsv now points each row to its specific raw artefact path and includes exact observed values (testcase names + paths + screenshots).
5. final-evidence-validator.txt refreshed to reflect updated coverage and ends `FINAL_EVIDENCE_VALIDATOR: PASS failures=0`.
6. Refreshed remote-proof and CHECKSUMS replay after this commit + tag recreation.

## Auditor verification command snippets

```bash
# Service repo
cd index-retriever-mcp-server
git fetch origin
git ls-remote origin refs/heads/w28e-614-index-retriever-xc
git ls-remote origin refs/tags/w28e-614-final-proof
git rev-parse w28e-614-final-proof^{}
sha256sum -c working/W28E-614-XC-WEBUI-ROLLOUT/CHECKSUMS.sha256

# UI monorepo
cd cloud-dog-ai-ui-monorepo
git fetch origin
git ls-remote origin refs/heads/w28e-614-index-retriever-ui
git ls-remote origin refs/tags/w28e-614-final-proof

# Live preprod
curl -sk https://indexretriever0.cloud-dog.net/health
curl -sk https://indexretriever0.cloud-dog.net/version
curl -sk -c /tmp/c.txt -X POST https://indexretriever0.cloud-dog.net/auth/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"OrangeRiverTable"}'
curl -sk -b /tmp/c.txt https://indexretriever0.cloud-dog.net/api/v1/admin/policies
```
