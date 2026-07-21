# index-retriever-mcp-server — Local Rules

## Common contract — binding

Read [the platform RULES](../cloud-dog-ai-platform-standards/RULES.md) and
`AGENT-LESSONS.md` in full before work. Central configuration, VDB, Gate 0 and
delivery controls apply; this file is an additive retrieval overlay.

**WebUI evidence (when applicable).** Browser-visible change or claim requires named real-service Playwright user-flow proof locally and again on final preprod `main`/`:latest`; `curl`, screenshots, DOM/unit checks, mocks and manual browsing are not substitutes. The platform rule governs the agent/auditor replay.

**Contested delivery (binding).** This repo and every lane it supports are shared space: recover/classify every dirty path, branch, worktree and collision with its owner; never use `BLOCKED` to abandon delivery. For any deployable change: develop/test locally → reconcile to `origin/main` → build final `:latest` → deploy only that `:latest` to PREPROD; never deploy a branch/SHA/old/local image or another environment.

## Local rules

- Preserve ingest, delete, search and retrieve lifecycle shaping across Web, API and
  MCP. Adapter and profile state must survive restart; one successful creation or
  a vector-store query alone is not durability proof.
- Source paths, upload URIs, metadata ownership and compatibility routes are current
  source/configuration contracts. Prove configured, retained and rejected paths in
  their actual execution environment.
- Use common storage/VDB/job contracts and surface required-field/provider errors;
  never convert a failed backend operation into a generic success envelope or direct
  database/vector-driver workaround.
- Security administration is a real UI/API contract for users, groups, keys and
  RBAC. Build and prove the paired UI and full selected profile lifecycle.

Historical installations, ports, direct probes and incidents are retired to Git history.

## External evidence

For every newly dispatched or re-dispatched lane, follow platform
`COMMON-EXTERNAL-EVIDENCE-ROOT-CONTRACT-2026-07-21.md`: write new raw proof only
to the allocated non-Git run root beneath `/opt/iac/Development/cloud-dog-ai/tmp/evidence`.
Git records identity references only; historical evidence remains untouched.
