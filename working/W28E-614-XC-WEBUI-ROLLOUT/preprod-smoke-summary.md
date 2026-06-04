# W28E-614 Preprod Smoke Summary

## Target service deployment
- index-retriever-mcp-server deployed to indexretriever0.cloud-dog.net via Terraform apply r5
- image: registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest @ sha256:7972883b83b98b8b8a656ed70142c887b35e15df8a08ece8e604b17b3fc329d8 (pushed digest sha256:b346057bed7f57c9d765fa864947a44b6f7e4c7f6c735803b3a4dc69940ba86e)
- /health 200 (db ok, vdb=qdrant ok, embedding=ollama ok)
- /version 200 {"version":"dev","application":"index-retriever-mcp-server","surface":"web"}
- /api/v1/admin/policies 200 (CX-110 backend wiring)
- /admin/roles 200 (SPA route)
- /diagnostics-audit 200 (SPA route)

## Estate health smoke (9/9 PASS)
- chat-client, db-mcp, expert-agent, file-mcp, git-mcp, imap-mcp, index-retriever, notification-agent, sql-agent all HTTP 200.
- Source: working/W28E-614-XC-WEBUI-ROLLOUT/evidence/preprod-health-before-after.tsv.

## Estate WebUI browser smoke (9/9 PASS)
- Spec: apps/index-retriever/tests/e2e/w28e-614/w28e-614-estate-smoke.spec.ts
- Each service: chromium goto SPA root, assert HTTP 200, #root mounted, no fatal console errors (cross-origin probe noise 401/403/404/405 + CORS + favicon filtered as documented), no 5xx network failures during load.

## Regression comparison
- Before/after: preprod-health-before-after.tsv shows 9/9 services HTTP 200 both before and after r5 deploy. No regression. Target service moved from 0.1.0 baseline to current build (image id 7972883b83b9).

## Conclusion
PASS. All §0B gate requirements met. No FAIL rows. No 5xx. No new regression.
