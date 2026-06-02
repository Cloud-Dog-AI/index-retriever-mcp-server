# Build Instructions

## Project
`index-retriever-mcp-server` - document indexing and retrieval service with parser and vector-backend plugins.

## Prerequisites
- Python 3.11+
- Docker with BuildKit support
- pip

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

If your platform packages are served from a package index:
```bash
PYPI_URL=https://packages.example.com/simple/
pip install -e ".[dev]" --extra-index-url "$PYPI_URL"
```

## Local Configuration
```bash
cat > .env.local <<'ENV'
CLOUD_DOG__API_SERVER__PORT=8074
CLOUD_DOG__WEB_SERVER__PORT=8075
CLOUD_DOG__MCP_SERVER__PORT=8076
CLOUD_DOG__A2A_SERVER__PORT=8077
EMBEDDING_BACKEND=ollama
VDB_BACKEND=chroma
PARSER_BACKEND=internal
ENV
```

## Run Locally
```bash
./server_control.sh --env ./.env.local start all
./server_control.sh --env ./.env.local status all
./server_control.sh --env ./.env.local stop all
```

## Run Tests
```bash
python -m pytest tests/quality --env ./.env.test -v
python -m pytest tests/unit --env ./.env.test -v
python -m pytest tests/system --env ./.env.test -v
python -m pytest tests/integration --env ./.env.test -v
python -m pytest tests/application --env ./.env.test -v
python -m pytest tests/parser --env ./.env.parsers -v
```

Use your own `.env.parsers` or `.env.test` file to switch parser providers, OCR settings, or vector database backends.

## Build
### Python Package
```bash
python -m pip install build
python -m build
```

### Docker Container
```bash
./docker-build.sh latest
```

Build with explicit package index and CA settings:
```bash
PYPI_URL=https://packages.example.com/simple/ \
PYPI_USERNAME=build-user \
PYPI_PASSWORD=build-password \
CUSTOM_CA_CERT=./certs/ca.pem \
./docker-build.sh latest
```

## Docker Push
```bash
docker tag cloud-dog/index-retriever-mcp-server:latest registry.example.com/team/index-retriever-mcp-server:latest
docker push registry.example.com/team/index-retriever-mcp-server:latest
```

## Configuration
The service loads environment variables, then the env file passed to `server_control.sh`, then `defaults.yaml`.

## Vault Integration
```bash
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=your-token
export VAULT_MOUNT_POINT=your-mount
export VAULT_CONFIG_PATH=your-path
```

## Publication test tag isolation (W28A-831)

`docker-build.sh` honours `PUBLICATION_TAG_SUFFIX` for building isolated
publication **test** images that never collide with dev/preprod/release tags
(default unset ⇒ behaviour unchanged):

```bash
PUBLICATION_TAG_SUFFIX=gitea-test ./docker-build.sh <version>
# builds <image>:<version>-gitea-test; internal registry tag is skipped
```

- Preview only: `PUBLICATION_DRY_RUN=1 PUBLICATION_TAG_SUFFIX=gitea-test ./docker-build.sh <version>`
- Cleanup: `cdci/scripts/publication-test-cleanup.sh gitea-test`
- Full reference: `cdci/docs/PUBLICATION-TAG-ISOLATION.md`
