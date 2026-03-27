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

# index-retriever-mcp-server — Docker Health Check (PS-91)
set -euo pipefail
PYTHON_BIN="python3"
if [[ -x "/app/.venv/bin/python" ]]; then
  PYTHON_BIN="/app/.venv/bin/python"
fi
API_PORT="$("${PYTHON_BIN}" - <<'PY'
from index_server.runtime_config import resolve_server_binding
print(resolve_server_binding("api_server").port)
PY
)"
curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null
