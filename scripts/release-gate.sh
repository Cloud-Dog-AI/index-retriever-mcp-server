#!/usr/bin/env bash
# index-retriever-mcp-server — Release gate
# Runs mandatory quality, compliance, and test checks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python3 -m ruff check src tests
python3 -m ruff format --check src tests
python3 -m mypy src

# Config delegation and separation checks
if grep -RIn "os\.environ\|import hvac\|overlay_secrets" src/index_tools --include='*.py'; then
  echo "Config delegation violation detected" >&2
  exit 1
fi
if grep -RIn "fastapi\|uvicorn\|starlette" src/index_tools --include='*.py'; then
  echo "Library/server separation violation detected" >&2
  exit 1
fi
if grep -RIn "FastAPI()" src --include='*.py'; then
  echo "Raw FastAPI() usage detected" >&2
  exit 1
fi
if grep -RIn "import chromadb\|import qdrant_client\|from chromadb\|from qdrant_client" src/index_tools --include='*.py'; then
  echo "Direct vector backend client import detected" >&2
  exit 1
fi
if grep -RIn "import openai\|from openai" src/index_tools --include='*.py'; then
  echo "Direct embedding client import detected" >&2
  exit 1
fi

bash scripts/validate-vault.sh
python3 -m pytest tests --env UT --env ST --env IT --env AT --env QT -q
python3 -m pytest tests/contract --env IT -q
python3 -m build --no-isolation

echo "Release gate passed"
