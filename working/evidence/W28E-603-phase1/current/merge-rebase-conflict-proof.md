# W28E-603 — merge / rebase / conflict proof (2026-06-05 no-cross-lane-waits amendment)

## Authoritative remote state
- Target repo: `index-retriever-mcp-server`. Lane branch: `w28e-603-phase1-structure` (isolated worktree
  `.w28e603-ir-wt`).
- `git fetch origin`; `git merge-base --is-ancestor origin/main HEAD` → **origin/main IS an ancestor of HEAD**.
  origin/main tip `7157c13` (2026-06-03, "fix W28A-829 index retriever docker e2e"). Nothing to merge/rebase
  from main — the lane already contains the current authoritative main. `git rev-list --left-right --count
  origin/main...HEAD` → `0  28` (0 behind, 28 ahead). No conflicts.

## Shared-package note — the api-kit 0.13.1 pin is NOT in this lane and NOT authoritative
- A first build attempt failed on `cloud-dog-api-kit==0.13.1` ("No matching distribution"; index max is 0.13.0).
- Root cause: the build was accidentally run from the **shared** `index-retriever-mcp-server` checkout, which a
  sibling lane had left on branch `fix/W28D-323-progress-aware-mcp-client` (commit `0146dc5`, 2026-06-05) — that
  branch pins `0.13.1`. `git merge-base --is-ancestor 0146dc5 HEAD` → **NO** (not in my history); 0146dc5 is on
  `origin/fix/W28D-323-progress-aware-mcp-client`, **not** on origin/main.
- This lane's worktree pins `cloud_dog_api_kit==0.13.0` in BOTH `pyproject.toml:18` and `Dockerfile:39`,
  identical to `origin/main:pyproject.toml`. The installed/tested venv is also 0.13.0 (full suite green).
- Resolution: build from the **isolated lane worktree** `.w28e603-ir-wt` (not the shared checkout). No package
  conflict exists in this lane; the W28D-323 0.13.1 work is a separate in-flight branch, owned by W28D-323, and
  is not part of W28E-603's authoritative state.

## Verdict
No Git/package/deploy conflicts to resolve in this lane. Authoritative remote state (origin/main) is fully
contained in HEAD. Builds run from the lane worktree.
