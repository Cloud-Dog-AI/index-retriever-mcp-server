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
# Usage: ./server_control.sh --env tests/env-UT {start|stop|restart|status} {api|mcp|all}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${SCRIPT_DIR}/.pids"
mkdir -p "${PID_DIR}"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

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
  # Safe key=value loader: exports plain values, skips ${vault.*} expressions
  # that are resolved by cloud_dog_config at Python runtime.
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    _line="${_line%%#*}"
    _line="${_line#"${_line%%[![:space:]]*}"}"
    [[ -z "$_line" || "$_line" != *=* ]] && continue
    _key="${_line%%=*}"; _val="${_line#*=}"
    [[ "$_val" == *'${vault.'* ]] && continue
    export "${_key}=${_val}"
  done < "${ENV_FILE}"
  shift 2
fi

ACTION="${1:-status}"
TARGET="${2:-all}"

# Module names are defined by the final server implementation.
declare -A MODULES=(
  [api]="index_server.api_server"
  [mcp]="index_server.mcp_server"
)

start_server() {
  local name="$1"
  local module="${MODULES[$name]}"
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
  TARGETS=(api mcp)
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
      echo "Usage: $0 [--env <file>] {start|stop|restart|status} {api|mcp|all}" >&2
      exit 1
      ;;
  esac
done
