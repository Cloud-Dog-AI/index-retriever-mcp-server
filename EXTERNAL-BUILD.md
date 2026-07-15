# External Build Guide — index-retriever-mcp-server

This document is self-contained. An external builder can clone this repository
from its public remote and build, run, smoke, and return evidence using ONLY
the information here plus a public package index. It does NOT require any
internal Cloud-Dog service, Vault, internal CA, internal registry, GitLab, or
any hidden sibling repository.

## 1. What this service is

`index-retriever-mcp-server` is an API-first MCP server for vector-database
indexing, search, and retrieval. It exposes four HTTP surfaces:

| Surface | Default port | Health / entry path        |
|---------|--------------|----------------------------|
| API     | 8074         | `/health`                  |
| Web UI  | 8075         | `/`                        |
| MCP     | 8076         | `/health`, `/mcp`          |
| A2A     | 8077         | `/health`, `/.well-known/agent.json` |

Defaults come from `defaults.yaml`. The config env-var prefix is
`CLOUD_DOG__INDEX__` (for example `CLOUD_DOG__INDEX__API_SERVER__PORT`); the API
base-path namespace is `CLOUD_DOG__INDEX_RETRIEVER__API_SERVER__BASE_PATH`.

## 2. Assumptions

- **Linux / macOS:** bash, Docker 24+ with BuildKit, CPython 3.13.14, `curl`.
- **Windows:** use WSL2 or Git Bash for the shell snippets; Docker Desktop with
  the WSL2 backend. PowerShell-native steps are not provided — run the bash
  blocks inside a Linux shell.
- A package index that serves the Cloud-Dog platform packages and their public
  dependencies. For an external (public) build this is public PyPI
  (`https://pypi.org/simple/`). Provide a different single index with `PYPI_URL`.
- No `--extra-index-url` is used anywhere (PS-97 §3.3 single-index rule). If a
  platform package is missing from the chosen index, STOP and report the gap —
  do not add a second index to work around it.

## 3. Path A — Docker build (recommended)

```bash
# 1. Build the public image (default variant=public; index is always explicit).
PYPI_URL=https://pypi.org/simple/ \
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh latest --variant public
#    -> builds cloud-dog/index-retriever-mcp-server:latest-pub-test

# 2. Smoke it (see PUBLICATION-SMOKE.md for the full block).
TAG=latest-pub-test bash -c "$(sed -n '/^```bash$/,/^```$/p' PUBLICATION-SMOKE.md | sed '1d;$d')"
```

The build uses a BuildKit secret (`pip_conf`) to carry the active index into
the build without baking it into image layers. To target a different index:

```bash
PYPI_URL=https://your-index.example.com/simple/ \
PIP_NETRC_FILE=/path/to/mode-0600-pip.netrc \
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh latest --variant public
```

The image installs the pinned platform packages and the project, runs as a
non-root user (`appuser`, uid 10001), and ships `server_control.sh`,
`docker-entrypoint.sh`, and `healthcheck.sh` at the paths the entrypoint uses.

## 4. Path B — pure source / package build (no Docker)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
# Single-index install. Override the index with PYPI_URL if needed.
pip install -e ".[dev]" --index-url "${PYPI_URL:-https://pypi.org/simple/}"

# Build a wheel/sdist:
pip install build
python -m build            # artefacts land in ./dist/

# Run locally with public-safe defaults:
cp docker-env.public.example .env.local
./server_control.sh --env ./.env.local start all
curl -fsS http://127.0.0.1:8074/health
./server_control.sh --env ./.env.local stop all
```

`lxml` and `xmlsec` are exact entries in `requirements.lock`. The chosen single
index must supply CPython 3.13-compatible wheels; the build does not install an
unfrozen OS compiler toolchain as a fallback.

## 5. Reproducibility

A pinned dependency manifest is provided. See `requirements.lock` (or
`requirements.lock.EXCEPTION.md` if a lock is not yet sealed) and the project
dependency declarations in `pyproject.toml` / `REQUIREMENTS.txt`. Install
exactly the locked versions with:

```bash
pip install --no-deps -r requirements.lock --index-url "${PYPI_URL:-https://pypi.org/simple/}"
```

## 6. Returning evidence

Place all build/run evidence under `external-build-evidence/` in the repo root,
then produce a checksummed tarball:

```bash
mkdir -p external-build-evidence
# Suggested contents:
#   docker-build.log                 (the build transcript)
#   image-digest.txt                 (docker inspect --format '{{.Id}}' <image>)
#   smoke.log                        (PUBLICATION-SMOKE.md output)
#   pip-freeze.txt                   (pip freeze from the build venv, Path B)
#   git-remote.txt                   (git remote -v — must show only the public remote)

tar -czf index-retriever-external-build-evidence.tgz external-build-evidence/
sha256sum index-retriever-external-build-evidence.tgz > index-retriever-external-build-evidence.tgz.sha256
```

Return the `.tgz` and its `.sha256` to the coordinator. Include the captured
image digest (`sha256:<hex>`) in your report for provenance.

## 7. Isolation checklist (PS-97 §3.5)

Print these in your report:

```
[ ] fresh venv / fresh clone (no cp -r, no branch-switch of an existing checkout)
[ ] git remote -v shows ONLY the public boundary remote (no gitlab / internal git)
[ ] no vendor/wheels, vendor/packages, .build-vendor in the clone
[ ] pip install used a single --index-url, no --extra-index-url (paste the command)
[ ] dependency resolution succeeded without fallback
[ ] docker build succeeded (paste final line) OR python -m build succeeded
[ ] image digest captured: sha256:<hex>
[ ] all platform packages resolved from the boundary index only
```
