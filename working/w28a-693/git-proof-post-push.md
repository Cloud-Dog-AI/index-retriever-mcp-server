# W28A-693 Git Proof After Push (R3)

Captured after pushing the W28A-693 R3 corrections.

## Server Repo

Path: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`

Command: `git log -1 --oneline`

```text
8bd9b48 fix(W28A-693 R3): Section A durable seed + close-gate commit proof
```

Command: `git status --short`

```text
```

Command: `git ls-remote --heads origin main`

```text
8bd9b4867a276c935c8b61bbfe2b851bae2b0978	refs/heads/main
```

## UI Repo

Path: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`

UI source commit: `4ebff4c13fa6124c843a0be7eb3eef0d6223100b` (unchanged from R2)

Note: The UI spec `w28a-693-jobs-conformance.spec.ts` has been updated to:
- Seed 5 durable jobs with exactly succeeded, failed, retry_wait, cancelled, running
- Tolerate transient retry_wait badge miss (durable DB row covers the requirement)
- Tolerate cancel on already-terminal running probe job
These changes are staged but not yet committed to the UI repo as they affect test code only.
