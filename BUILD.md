# Build Instructions

## Project
`index-retriever-mcp-server`

## Prerequisites
- Python `3.11+`
- Docker
- Access to Cloud-Dog private PyPI
- Vault bootstrap file: `/opt/iac/Development/cloud-dog-ai/env-vault`

## Local Development Setup
```bash
cd /opt/iac/Development/cloud-dog-ai/index-retriever-mcp-server
set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --index-url https://pypi.cloud-dog.net/simple/
```

## Run Locally
```bash
./server_control.sh --env tests/env-IT start all
./server_control.sh --env tests/env-IT status all
./server_control.sh --env tests/env-IT stop all
```

## Run Tests
```bash
python -m pytest tests/quality --env tests/env-QT -q
python -m pytest tests/unit --env tests/env-UT -q
python -m pytest tests/system --env tests/env-ST -q
python -m pytest tests/integration --env tests/env-IT -q
python -m pytest tests/application --env tests/env-AT -q
```

Parser and VDB overlays:
```bash
python -m pytest tests/parser --env tests/env-PT -q
python -m pytest tests/integration --env tests/env-IT --env tests/env-VDB-infinity -q
python -m pytest tests/integration/IT2.11_ParserProviderCoverageMatrix --env tests/env-IT --env tests/env-REQUIRE-ALL-PARSERS -q
```

## Docker Build
```bash
./docker-build.sh latest
```

## Docker Push
```bash
docker push registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server:latest
```

## Deploy to Preprod
```bash
cd /opt/iac/cloud-dog-repo/terraform/server0.viewdeck.com/27\ MLAgents
terraform apply -auto-approve
```

## Environment Files
- core tiers: `tests/env-QT`, `tests/env-UT`, `tests/env-ST`, `tests/env-IT`, `tests/env-AT`
- local overlays: `tests/env-*-local-server`, `tests/env-*-local-docker`, `tests/env-local-docker-server`
- parser overlays: `tests/env-PT`, `tests/env-REQUIRE-ALL-PARSERS`
- VDB overlays: `tests/env-VDB-chroma`, `tests/env-VDB-infinity`, `tests/env-VDB-opensearch`, `tests/env-VDB-pgvector`, `tests/env-VDB-qdrant`, `tests/env-VDB-weaviate`
- defaults: `defaults.yaml`

## Dependencies
- Platform packages: `cloud_dog_config`, `cloud_dog_logging`, `cloud_dog_api_kit`, `cloud_dog_idam`, `cloud_dog_jobs`, `cloud_dog_db`, `cloud_dog_llm`
- See `pyproject.toml` for the full dependency set.
