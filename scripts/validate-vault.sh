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

# index-retriever-mcp-server — Vault validation script
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Validates Vault connectivity and required configuration sections.

set -euo pipefail

if [[ -f "/opt/iac/Development/cloud-dog-ai/env-vault" ]]; then
  set -a
  # shellcheck disable=SC1091
  source /opt/iac/Development/cloud-dog-ai/env-vault
  set +a
fi

required_vars=(VAULT_ADDR VAULT_TOKEN VAULT_MOUNT_POINT VAULT_CONFIG_PATH)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required Vault variable: ${var}" >&2
    exit 1
  fi
done

response="$(curl -fsS -H "X-Vault-Token: ${VAULT_TOKEN}" \
  "${VAULT_ADDR}/v1/${VAULT_MOUNT_POINT}/data/${VAULT_CONFIG_PATH}")"

python3 -c '
import json
import sys

payload = json.load(sys.stdin)
raw_data = payload.get("data", {}).get("data", {})

config = {}
if isinstance(raw_data, dict):
    # Preferred shape: data.data.dev
    if isinstance(raw_data.get("dev"), dict):
        config = raw_data
    # Common wrapped shape: data.data.json.dev
    elif isinstance(raw_data.get("json"), dict):
        config = raw_data["json"]
    # Fallback: data.data.content contains JSON string with "dev"
    elif isinstance(raw_data.get("content"), str):
        try:
            parsed = json.loads(raw_data["content"])
            if isinstance(parsed, dict):
                config = parsed
        except json.JSONDecodeError:
            config = {}

required_sections = ["dev.models", "dev.vdbs", "dev.databases", "dev.storage", "dev.redis", "dev.repository"]

missing = []
for section in required_sections:
    cursor = config
    for part in section.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            missing.append(section)
            break
        cursor = cursor[part]

if missing:
    print("Missing required Vault sections:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)

print("Vault validation successful. Required sections available.")
' <<<"${response}"
