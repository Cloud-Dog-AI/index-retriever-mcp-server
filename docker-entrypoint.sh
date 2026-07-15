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

# index-retriever-mcp-server — Docker Entrypoint (PS-91)
set -euo pipefail

echo "============================================================"
echo "index-retriever-mcp-server container"
echo "Mode: ${1:-all} | Python: $(python3 --version 2>&1)"
echo "============================================================"

mkdir -p /app/logs /app/data /app/.pids /app/certs

# ── CA Bundle ────────────────────────────────────────────────────
CA_PATH="${CLOUD_DOG_TLS_CA_BUNDLE:-${REQUESTS_CA_BUNDLE:-}}"
if [[ -n "${CA_PATH}" && -f "${CA_PATH}" ]]; then
  cp "${CA_PATH}" /usr/local/share/ca-certificates/custom-ca.crt
  update-ca-certificates 2>/dev/null || true
fi
export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
export GIT_SSL_CAINFO="${GIT_SSL_CAINFO:-/etc/ssl/certs/ca-certificates.crt}"
export NODE_EXTRA_CA_CERTS="${NODE_EXTRA_CA_CERTS:-/etc/ssl/certs/ca-certificates.crt}"

# ── Env file loading ────────────────────────────────────────────
ENV_FILE="${CLOUD_DOG_ENV_FILE:-}"
ENV_ARGS=()
if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
  ENV_ARGS=(--env "${ENV_FILE}")
fi

PYTHON_BIN="python3"
if [[ -x "/app/.venv/bin/python" ]]; then
  PYTHON_BIN="/app/.venv/bin/python"
fi

api_port() {
  "${PYTHON_BIN}" - <<'PY'
from index_server.runtime_config import resolve_server_binding
print(resolve_server_binding("api_server").port)
PY
}

# ── Graceful shutdown ───────────────────────────────────────────
shutdown() {
  echo "[INFO] Stopping services..."
  /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} stop all 2>/dev/null || true
}
trap shutdown INT TERM

# ── Mode dispatch ───────────────────────────────────────────────
case "${1:-all}" in
  all)
    /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} start all
    tail -F /app/logs/*.log 2>/dev/null &
    wait $!
    ;;
  api|web|mcp|a2a)
    /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} start "$1"
    tail -F /app/logs/*.log 2>/dev/null &
    wait $!
    ;;
  status)
    /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} status all
    ;;
  test)
    /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} start api
    sleep 5
    if "${PYTHON_BIN}" - "$(api_port)" <<'PY'
from __future__ import annotations

import sys
import urllib.request

with urllib.request.urlopen(f"http://127.0.0.1:{int(sys.argv[1])}/health", timeout=5) as response:
    response.read()
    raise SystemExit(0 if response.status == 200 else 1)
PY
    then
      echo "HEALTH CHECK PASSED"
      /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} stop all
      exit 0
    else
      echo "HEALTH CHECK FAILED"
      /app/server_control.sh ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} stop all
      exit 1
    fi
    ;;
  shell|bash)
    exec /bin/bash
    ;;
  *)
    echo "Usage: index-retriever-mcp-server [all|api|web|mcp|a2a|status|test|shell]"
    exit 1
    ;;
esac
