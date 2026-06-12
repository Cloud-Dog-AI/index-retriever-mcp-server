---
template-id: T-BLD
template-version: 1.0
applies-to: docs/BUILD.md
registry: service
required: must-have
when-applicable: ""
template-last-updated: 2026-06-12
template-owner: platform-standards

project: index-retriever-mcp-server
doc-last-updated: 2026-06-12
doc-git-commit: 5cba8eb76245a4d7ba5af6f0b3b765199a6f6ee6
doc-git-branch: main
doc-source-shas: []
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# index-retriever-mcp-server — BUILD (from source)

> **Template version:** T-BLD v1.0 — internal from-source build instructions.

## 1. Prerequisites
Python/Node version, system packages, internal PyPI index, Gitea boundary index, vault env.

## 2. Build steps
**You MUST include:** the exact commands a fresh agent runs to produce a working image.

```bash
# 1. clone
git clone <repo>
cd <repo>

# 2. env
source /opt/iac/.../env-vault

# 3. build
./docker-build.sh
```

## 3. Variants
dev / public / multilang etc — when to use each.

## 4. Outputs
Image name, digest location, smoke command.

## 5. Cross-references
- [DEPLOY.md](DEPLOY.md)
- [DOCKER.md](DOCKER.md)
- [EXTERNAL-BUILD.md](../EXTERNAL-BUILD.md) — public-facing build
- PS-96-build.md

## 6. Project-specific notes
