# W28E-603 — sentinel WebUI smoke (after preprod deploy)

Date context: 2026-06-05. Real headless chromium (Playwright 1.58.2, monorepo browsers) loading each sentinel
SPA root, verifying render/mount + capturing console errors + page exceptions. Run after indexretriever0 deploy.

| service | http | title | SPA mounted | fatal JS / pageerror | note |
|---|---|---|---|---|---|
| chatclient0 | 200 | Cloud-Dog : Chat client | yes | none | 9 console msgs = expected 401 resource fetches (unauthenticated landing) |
| expertagent0 | 200 | Cloud-Dog : Expert Agent | yes | none | 0 console errors |
| notificationagent0 | 200 | Cloud-Dog : Notification agent | yes | none | 1 console msg = expected 401 (unauthenticated) |
| filemcpserver0 | 200 | Cloud-Dog File MCP | yes | none | 1 console msg = expected 401 (unauthenticated) |
| dbmcpserver0 | 200 | Cloud-Dog DB MCP | yes | none | 0 console errors |

VERDICT: 5/5 sentinel WebUIs load + render (SPA mounted, correct titles) in a real browser with NO fatal JS
errors or page exceptions. The only console errors are expected HTTP 401s from API calls on the unauthenticated
landing page (no login performed). Estate WebUIs healthy after the targeted indexretriever0 deploy.
