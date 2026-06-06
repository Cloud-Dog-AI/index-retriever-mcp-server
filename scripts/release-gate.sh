#!/usr/bin/env bash
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

python3 -m pytest tests --env UT --env ST --env IT --env AT --env QT -q
python3 -m pytest tests/contract --env IT -q
python3 -m build --no-isolation

echo "Release gate passed"
