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

# index-retriever-mcp-server — Server control script
# Usage: ./server_control.sh --env tests/env-UT {start|stop|restart|status} {api|web|mcp|a2a|all}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${SCRIPT_DIR}/.pids"
mkdir -p "${PID_DIR}"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"

resolve_python_bin() {
  local candidate="${SCRIPT_DIR}/.venv/bin/python"
  if [[ -x "${candidate}" ]]; then
    if "${candidate}" - <<'PY' >/dev/null 2>&1
import importlib.util

required = [
    "cloud_dog_config",
    "cloud_dog_logging",
    "cloud_dog_api_kit",
    "cloud_dog_idam",
    "cloud_dog_db",
]
missing = [name for name in required if importlib.util.find_spec(name) is None]
raise SystemExit(0 if not missing else 1)
PY
    then
      printf '%s\n' "${candidate}"
      return
    fi
  fi
  printf '%s\n' "python3"
}

PYTHON_BIN="$(resolve_python_bin)"

LOG_DIR="${CLOUD_DOG_LOG_DIR:-/app/logs}"
if ! mkdir -p "${LOG_DIR}" 2>/dev/null; then
  LOG_DIR="${SCRIPT_DIR}/logs"
  mkdir -p "${LOG_DIR}"
fi

ENV_FILE=""
if [[ "${1:-}" == "--env" ]]; then
  ENV_FILE="${2:-}"
  if [[ -z "${ENV_FILE}" || ! -f "${ENV_FILE}" ]]; then
    echo "Missing or invalid --env file" >&2
    exit 1
  fi
  export CLOUD_DOG_ENV_FILES="${ENV_FILE}"
  shift 2
fi

hydrate_plain_env_from_file() {
  [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]] || return 0
  eval "$("${PYTHON_BIN}" - "${ENV_FILE}" <<'PY'
from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

VAULT_REF_PATTERN = re.compile(r"^\$\{(vault\.[^}]+)\}$")

try:
    from cloud_dog_config.compiler.vault_resolver import resolve_vault_identifier
    from cloud_dog_config.vault.client import VaultClient, VaultConnectionConfig
except Exception:
    resolve_vault_identifier = None
    VaultClient = None
    VaultConnectionConfig = None


def resolve_value(raw: str) -> str:
    value = raw.strip()
    match = VAULT_REF_PATTERN.match(value)
    if match is None or resolve_vault_identifier is None:
        return value

    addr = os.environ.get("VAULT_ADDR", "").strip()
    token = os.environ.get("VAULT_TOKEN", "").strip()
    if not addr or not token or VaultClient is None or VaultConnectionConfig is None:
        return value

    mount = os.environ.get("VAULT_MOUNT_POINT", "").strip().strip("/")
    config_path = os.environ.get("VAULT_CONFIG_PATH", "").strip().strip("/")
    if config_path:
        mount = "/".join(part for part in (mount, config_path) if part)

    try:
        client = VaultClient(
            VaultConnectionConfig(
                server=addr,
                token=token,
                timeout_seconds=10.0,
                mount_point=mount,
            )
        )
        resolved = resolve_vault_identifier(match.group(1), vault=client)
    except Exception:
        return value

    if isinstance(resolved, (str, int, float, bool)):
        text = str(resolved).strip()
        if text:
            return text
    return value


env_path = Path(sys.argv[1]).resolve()
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if not key or key.startswith("CLOUD_DOG__") or key.startswith("CLOUD_DOG_DB__"):
        continue
    print(f"export {key}={shlex.quote(resolve_value(value))}")
PY
  )"
}

hydrate_plain_env_from_file

ACTION="${1:-status}"
TARGET="${2:-all}"

# Module names are defined by the final server implementation.
declare -A MODULES=(
  [api]="index_server.api_server"
  [web]="index_server.web_server"
  [mcp]="index_server.mcp_server"
  [a2a]="index_server.a2a_server"
)

declare -A BINDINGS=(
  [api]="api_server"
  [web]="web_server"
  [mcp]="mcp_server"
  [a2a]="a2a_server"
)

resolve_server_port() {
  local name="$1"
  "${PYTHON_BIN}" - "${BINDINGS[$name]}" <<'PY'
from __future__ import annotations

import sys

from index_server.runtime_config import resolve_server_binding

binding = resolve_server_binding(sys.argv[1])
print(int(binding.port))
PY
}

wait_for_server_port() {
  local name="$1"
  local port="$2"
  local timeout_seconds="${3:-30}"
  local host="${4:-127.0.0.1}"
  local start_time
  start_time="$(date +%s)"
  while true; do
    if command -v ss >/dev/null 2>&1; then
      if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|:)${port}$"; then
        return 0
      fi
    elif command -v netstat >/dev/null 2>&1; then
      if netstat -tln 2>/dev/null | awk '{print $4}' | grep -qE "(^|:)${port}$"; then
        return 0
      fi
    elif command -v lsof >/dev/null 2>&1; then
      if lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -qE "[\\.:]${port}[[:space:]]"; then
        return 0
      fi
    elif "${PYTHON_BIN}" - "${host}" "${port}" <<'PY' >/dev/null 2>&1
from __future__ import annotations

import socket
import sys

host = sys.argv[1].strip() or "127.0.0.1"
if host in {"0.0.0.0", "::", "[::]"}:
    host = "127.0.0.1"
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.5)
    raise SystemExit(0 if sock.connect_ex((host, port)) == 0 else 1)
PY
    then
      return 0
    fi
    if ! kill -0 "$(cat "${PID_DIR}/${name}.pid" 2>/dev/null)" 2>/dev/null; then
      return 1
    fi
    if (( $(date +%s) - start_time >= timeout_seconds )); then
      return 1
    fi
    sleep 0.5
  done
}

start_server() {
  local name="$1"
  local module="${MODULES[$name]}"
  local port=""
  local pid_file="${PID_DIR}/${name}.pid"
  local log_file="${LOG_DIR}/${name}.log"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name}: running (PID $(cat "${pid_file}"))"
    return
  fi
  PYTHONUNBUFFERED=1 PYTHONFAULTHANDLER=1 nohup "${PYTHON_BIN}" -m "${module}" >"${log_file}" 2>&1 < /dev/null &
  local pid=$!
  echo "${pid}" > "${pid_file}"
  sleep 0.5
  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "${name}: failed to start (see ${log_file})" >&2
    rm -f "${pid_file}"
    return 1
  fi
  port="$(resolve_server_port "${name}")"
  if [[ -n "${port}" ]] && ! wait_for_server_port "${name}" "${port}" 45 "127.0.0.1"; then
    echo "${name}: failed to bind port ${port} (see ${log_file})" >&2
    rm -f "${pid_file}"
    return 1
  fi
  echo "${name}: started (PID ${pid})"
}

stop_server() {
  local name="$1"
  local module="${MODULES[$name]}"
  local pid_file="${PID_DIR}/${name}.pid"

  terminate_pid() {
    local target_pid="$1"
    if ! kill -0 "${target_pid}" 2>/dev/null; then
      return
    fi
    kill "${target_pid}" 2>/dev/null || true
    for _ in {1..20}; do
      if ! kill -0 "${target_pid}" 2>/dev/null; then
        return
      fi
      sleep 0.1
    done
    kill -9 "${target_pid}" 2>/dev/null || true
  }

  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}")"
    terminate_pid "${pid}"
    rm -f "${pid_file}"
  fi

  while read -r orphan_pid; do
    terminate_pid "${orphan_pid}"
  done < <(pgrep -f " -m ${module}( |$)" || true)

  echo "${name}: stopped"
}

status_server() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    echo "${name}: running (PID $(cat "${pid_file}"))"
  else
    echo "${name}: stopped"
  fi
}

if [[ "${TARGET}" == "all" ]]; then
  TARGETS=(api web mcp a2a)
else
  TARGETS=("${TARGET}")
fi

for server in "${TARGETS[@]}"; do
  case "${ACTION}" in
    start) start_server "${server}" ;;
    stop) stop_server "${server}" ;;
    restart) stop_server "${server}"; sleep 1; start_server "${server}" ;;
    status) status_server "${server}" ;;
    *)
      echo "Usage: $0 [--env <file>] {start|stop|restart|status} {api|web|mcp|a2a|all}" >&2
      exit 1
      ;;
  esac
done
