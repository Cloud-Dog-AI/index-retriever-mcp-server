---
doc-id: RELEASE-1.0RC01
project: index-retriever-mcp-server
doc-last-updated: 2026-06-25T08:00:14Z
doc-git-commit: W28E-1805C-closeout
doc-git-branch: main
---

# index-retriever-mcp-server - 1.0RC01 Release Notes

## Scope

1.0RC01 closes W28E-1805C Stream-C for the index-retriever WebUI/E2E release path. It preserves the W28E-1805B document-structure surface and fixes the send-back blockers around local Docker build, WebUI/API runtime state, IDAM API-key mode, and full browser E2E.

## Changes

- Docker dev build now uses the approved internal package index with non-interactive pip and no secondary package index.
- WebUI tool proxy calls now reach the API tool surface so admin WebUI mutations and tool calls share runtime state.
- `/status` and `/api/status` now return the rich runtime status payload consistently.
- Search responses now preserve vector hits and backfill missing local lexical matches up to `top_k`, fixing upload/search visibility for exact document content.
- Playwright API-key login fallback is hardened for local Docker and preprod-like runs.

## Verification

- Service unit regression: `service-unit-search-local-backfill-env.log`, 2 passed.
- Web proxy unit regression: `service-unit-web-tool-proxy-api-forward-env-rerun.log`, 1 passed.
- UI typecheck/build: `ui-typecheck-web-proxy-api-forward.log`, `ui-build-web-proxy-api-forward.log`.
- Local Docker build: `local-docker-build-search-backfill-vault-simple.log`, image `sha256:08a38c1ef8c13580a696cb7ed79db4dbd5a468cf1e690d99b59d3e3b7d691d7e`.
- Full WebUI/E2E: `local-docker-webui-playwright-search-backfill-full-clean.log`, 76 passed.

## Release Evidence

The release evidence pack is `cloud-dog-ai-platform-standards/working/evidence/W28E-1805C/current/`.
