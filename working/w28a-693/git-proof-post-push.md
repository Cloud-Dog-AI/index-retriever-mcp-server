# W28A-693 Git Proof Anchor

This committed file is the R4 proof-anchor record. It intentionally does not
claim that the pre-commit hash is the final returned commit. The immutable final
raw proof is recorded after this commit is pushed in annotated tag
`W28A-693-R4-FINAL-PROOF`.

## Server Repo

Path: `/opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server`

Final proof command: `git rev-parse HEAD`

```text
See annotated tag W28A-693-R4-FINAL-PROOF.
```

Final proof command: `git ls-remote origin refs/heads/main`

```text
See annotated tag W28A-693-R4-FINAL-PROOF.
```

Final proof command: `git status --short`

```text
See annotated tag W28A-693-R4-FINAL-PROOF.
```

Final proof command: `git ls-files working/w28a-693/ | wc -l`

```text
See annotated tag W28A-693-R4-FINAL-PROOF.
```

Command: `git ls-files <W28A-693 source/evidence paths>`

```text
src/index_server/mcp_server.py
src/index_tools/tools/definitions.py
src/index_tools/tools/registry.py
src/index_tools/tools/service.py
working/w28a-693/06-rules-warranty.md
working/w28a-693/close-gate.md
working/w28a-693/docker/junit.xml
working/w28a-693/docker/test-results/e2e-w28a-693-jobs-conforma-7a8b9-76-v2-Jobs-page-conformance-chromium/trace.zip
working/w28a-693/evidence-matrix-summary.log
working/w28a-693/local-code/junit.xml
working/w28a-693/local-code/test-results/e2e-w28a-693-jobs-conforma-7a8b9-76-v2-Jobs-page-conformance-chromium/trace.zip
working/w28a-693/playwright-trace-proof.log
```

## UI Repo

Path: `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-ui-monorepo`

Command: `git log -1 --oneline`

```text
16da675 fix(index-retriever): source-backed W28A-693 conformance evidence
```

Command: `git rev-parse HEAD`

```text
16da675d6aa9e05cb334d5d92ac674abf715f6b3
```

Command: `git status --short -- apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text

```

Command: `git ls-remote --heads origin main`

```text
16da675d6aa9e05cb334d5d92ac674abf715f6b3	refs/heads/main
```

Final UI remote/scoped status proof is also recorded in annotated tag
`W28A-693-R4-FINAL-PROOF`.

Command: `git ls-files apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts`

```text
apps/index-retriever/tests/e2e/w28a-693-jobs-conformance.spec.ts
```
