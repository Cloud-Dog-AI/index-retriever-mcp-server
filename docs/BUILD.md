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
doc-last-updated: 2026-07-15
doc-git-commit: W28R-3016-pending-main
doc-git-branch: w28r-3016-index-retriever
doc-source-shas: [Dockerfile, docker-build.sh, requirements.lock, pyproject.toml]
doc-age-policy: 90d
doc-conformance-stamp: 2026-06-12T12:00:00Z
---

# index-retriever-mcp-server — BUILD (from source)

> **Template version:** T-BLD v1.0 — internal from-source build instructions.

## 1. Prerequisites

- CPython 3.13.14 for source tests and package work.
- Docker 24 or newer with BuildKit/buildx.
- An explicit single package index in `PYPI_URL`.
- A mode-0600 netrc helper in `PIP_NETRC_FILE` for the private dev boundary.
- The internal dev build uses the digest-pinned
  `registry.cloud-dog.net:443/cloud-dog/python-runtime:3.13-slim-20260713`
  base. The public build uses `python:3.13-slim`.

## 2. Build steps
The release build consumes the exact versions in `requirements.lock`; it never
uses an extra index or a package-index fallback.

```bash
# 1. create the project-local Python 3.13 environment
python3.13 -m venv .venv

# 2. install and test from the explicit single index
PIP_INDEX_URL="${PYPI_URL:?set the release-selected index}" \
  .venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest tests/quality --env tests/env-QT -q
.venv/bin/python -m pytest tests/unit --env tests/env-UT -q

# 3. build the internal image directly under its internal-registry name
REGISTRY=registry.cloud-dog.net:443 \
PYPI_URL=https://pypi.cloud-dog.net/simple/ \
PIP_NETRC_FILE="${PIP_NETRC_FILE:?provide a mode-0600 netrc helper}" \
./docker-build.sh latest --variant dev
```

## 3. Variants
- `--variant dev`: internal release/deployment image; uses `Dockerfile`, the
  internal digest-pinned Python 3.13 base, and requires an external netrc.
- `--variant public`: closed-loop publication build; uses `Dockerfile.public`
  and requires an explicit `PYPI_URL`. Use `PUBLICATION_TAG_SUFFIX` for an
  isolated publication test tag.

## 4. Outputs
- Dev output: `registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:<tag>`.
- Public output: `cloud-dog/index-retriever-mcp-server:<tag>[-suffix]`.
- Inspect the immutable local image ID with
  `docker image inspect --format '{{.Id}}' <image>`.
- Run the public smoke contract in `PUBLICATION-SMOKE.md`; internal local-Docker
  flows use `local-docker-server.sh` with an explicit env file and package boundary.

## 5. Cross-references
- [DEPLOY.md](DEPLOY.md)
- [DOCKER.md](DOCKER.md)
- [EXTERNAL-BUILD.md](../EXTERNAL-BUILD.md) — public-facing build
- PS-96-build.md

## 6. Project-specific notes

Credentials are never accepted in `PYPI_URL` or build arguments. The build
mounts `pip_conf` and `pip_netrc` only as BuildKit secrets. The compiled WebUI
under `ui/dist/` must be regenerated from the UI monorepo; do not edit it by hand.
