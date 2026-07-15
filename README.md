---
template-id: T-RME
template-version: 1.0
applies-to: README.md
---

# Index Retriever MCP Server

`index-retriever-mcp-server` exposes document ingestion, retrieval, parser, Web UI, MCP, and A2A-compatible endpoints.

## Publication Quick Start

Prerequisites:

- Docker 24 or newer with BuildKit enabled
- Python 3.12 or newer if you run the package locally
- A package index that serves the Cloud-Dog platform packages and their public
  dependencies (public PyPI for external builds; supply via `PYPI_URL`)

Build the public publication image (default variant):

```bash
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh latest
```

Run the local smoke by executing the shell block in [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md) with `TAG=latest-pub-test`.

The smoke run uses [docker-env.public.example](docker-env.public.example) and probes:

- API: `8074`
- Web: `8075`
- MCP: `8076`
- A2A: `8077`

See [EXTERNAL-BUILD.md](EXTERNAL-BUILD.md) for the full self-contained external-builder guide.

## Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
# Point PYPI_URL at the index that serves the cloud-dog platform packages.
pip install -e ".[dev]" --index-url "${PYPI_URL:-https://pypi.org/simple/}"
```

Runtime configuration is loaded from the env file passed to `server_control.sh`, then from shell environment variables, then from `defaults.yaml`.

### Storage profiles

A clean install ships exactly one storage profile, `default`. Additional
demo/reference profiles (Transparent Borders, NATO, Ukraine, multilang) are **not**
shipped in `defaults.yaml`; they live in the opt-in `config/demo-profiles.yaml` and
load only when demo profiles are explicitly enabled:

```bash
# Opt in to the demo/reference profile suite (demo/dev/preprod environments only).
CLOUD_DOG__INDEX__DEMO_PROFILES__ENABLED=true
# Optional: point at a specific demo-profiles file
# (defaults to /app/config/demo-profiles.yaml in the container).
CLOUD_DOG__INDEX__DEMO_PROFILES__PATH=/app/config/demo-profiles.yaml
```

With the flag unset (the shipped default), `profiles_list` returns only `default` —
no demo/test profile data is shipped in the production artifact.

## Documentation

- [BUILD.md](BUILD.md)
- [EXTERNAL-BUILD.md](EXTERNAL-BUILD.md)
- [PUBLICATION-SMOKE.md](PUBLICATION-SMOKE.md)
- [docker-env.public.example](docker-env.public.example)

## Licence

Apache-2.0 - Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited

## Security & Publication Notes

Authentication and authorisation use the platform IDAM credential/cert model; do not commit secrets.
This public source mirror excludes internal operations material; build artefacts (e.g. the UI bundle) are regenerated at build time.
