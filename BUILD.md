---
template-id: T-BLD
template-version: 1.0
applies-to: BUILD.md
---

# Build Instructions

## Project
`index-retriever-mcp-server` - document indexing and retrieval service with parser and vector-backend plugins.

## Prerequisites
- Python 3.12+
- Docker with BuildKit support
- pip

## Development Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

If your platform packages are served from a single package index, point
`--index-url` at it (single-index install; do not mix multiple indexes):
```bash
PYPI_URL="${PYPI_URL:-https://pypi.org/simple/}"
pip install -e ".[dev]" --index-url "$PYPI_URL"
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
# Public variant (default): index defaults to https://pypi.org/simple/
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh latest --variant public
```

Build with an explicit package index and (dev variant) CA settings:
```bash
PYPI_URL=https://pypi.org/simple/ \
PYPI_USERNAME=build-user \
PYPI_PASSWORD=build-password \
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh latest --variant public
```

The `--variant dev` selector builds the internal `Dockerfile` and defaults its
index/CA to the internal developer environment; it is not used for publication.

## Docker Push
```bash
docker tag cloud-dog/index-retriever-mcp-server:latest registry.example.com/team/index-retriever-mcp-server:latest
docker push registry.example.com/team/index-retriever-mcp-server:latest
```

## Configuration
The service loads environment variables, then the env file passed to `server_control.sh`, then `defaults.yaml`.

## Local Secrets
Put local-only values in the env file passed to `server_control.sh` or mounted into Docker. Do not commit real credentials.

## Publication test tag isolation (W28A-831)

`docker-build.sh` honours `PUBLICATION_TAG_SUFFIX` for building isolated
publication **test** images that never collide with reserved runtime/release tags
(default unset ⇒ behaviour unchanged):

```bash
PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh <version>
# builds <image>:<version>-pub-test; registry tag is skipped
```

- Preview only: `PUBLICATION_DRY_RUN=1 PUBLICATION_TAG_SUFFIX=pub-test ./docker-build.sh <version>`
