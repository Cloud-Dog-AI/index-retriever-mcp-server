# Build Guide — index-retriever-mcp-server

## Prerequisites
- Python `3.11+`
- `pip` with access to private package index `https://pypi.cloud-dog.net/simple/`
- Vault bootstrap file: `/opt/iac/Development/cloud-dog-ai/env-vault`
- Docker engine (for container build)

## Local Development Setup

```bash
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

## Build Python Package

```bash
source .venv/bin/activate
python -m build
```

Output artifacts are written to `dist/`.

## Build Docker Image

Use the project-standard wrapper (not ad-hoc docker build):

```bash
./docker-build.sh
```

If a specific tag is needed:

```bash
IMAGE_TAG=latest ./docker-build.sh
```

## Lint and Type Check

```bash
source .venv/bin/activate
ruff check src tests
mypy src
```

## Test Execution by Tier

Always pass env files explicitly.

```bash
source .venv/bin/activate

python -m pytest tests/quality --env tests/env-QT -q
python -m pytest tests/unit --env tests/env-UT -q
python -m pytest tests/system --env tests/env-ST -q
python -m pytest tests/integration --env tests/env-IT -q
python -m pytest tests/application --env tests/env-AT -q
```

Optional parser/performance tiers:

```bash
python -m pytest tests/contract --env tests/env-IT -q
python -m pytest tests/parser --env tests/env-PT -q
```

## Runtime Startup for Build Validation

```bash
./server_control.sh --env tests/env-IT start all
./server_control.sh --env tests/env-IT status all
./server_control.sh --env tests/env-IT stop all
```
