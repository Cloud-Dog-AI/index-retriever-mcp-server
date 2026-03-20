#!/usr/bin/env bash
# Wrapper maintained for instruction compatibility.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"
exec bash "${PROJECT_ROOT}/docker-build.sh" "$@"
