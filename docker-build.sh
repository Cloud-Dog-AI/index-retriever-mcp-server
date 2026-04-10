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

# index-retriever-mcp-server — Docker Build Script (PS-91)
# Uses BuildKit secret mount for private PyPI auth — credentials never enter image layers.
set -euo pipefail

VERSION="${1:-latest}"
CONTAINER="index-retriever-mcp-server"
FOLDER="cloud-dog"
REGISTRY="registry.cloud-dog.net:443"
CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-/usr/local/share/ca-certificates/cloud-dog.net.ca.crt}"
GENERIC_CA_CERT="custom-ca.crt"
CERT_ARG=""
PIP_CONF=".pip.conf.build"
LOCAL_WHEEL_DIR="vendor/wheels"
LOCAL_PLATFORM_WHEEL_GLOBS=(
  "${LOCAL_WHEEL_DIR}/cloud_dog_config-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_logging-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_api_kit-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_idam-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_db-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_jobs-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_storage-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_llm-*.whl"
  "${LOCAL_WHEEL_DIR}/cloud_dog_vdb-*.whl"
)

echo "=========================================="
echo "Docker Build: ${FOLDER}/${CONTAINER}:${VERSION}"
echo "=========================================="

# ── Local wheel fallback ────────────────────────────────────────
USE_LOCAL_PLATFORM_WHEELS=1
shopt -s nullglob
for pattern in "${LOCAL_PLATFORM_WHEEL_GLOBS[@]}"; do
  matches=( ${pattern} )
  if [[ ${#matches[@]} -eq 0 ]]; then
    USE_LOCAL_PLATFORM_WHEELS=0
    break
  fi
done
shopt -u nullglob

# ── Private PyPI credentials ─────────────────────────────────────
PYPI_URL="${PYPI_URL:-https://pypi.cloud-dog.net/simple/}"
PYPI_USERNAME="${PYPI_USERNAME:-}"
PYPI_PASSWORD="${PYPI_PASSWORD:-}"

if [[ ${USE_LOCAL_PLATFORM_WHEELS} -eq 0 && ( -z "${PYPI_USERNAME}" || -z "${PYPI_PASSWORD}" ) ]]; then
  if [[ -f /opt/iac/Development/cloud-dog-ai/env-vault ]]; then
    source /opt/iac/Development/cloud-dog-ai/env-vault
    VAULT_JSON=$(curl -fsS \
      -H "X-Vault-Token: ${VAULT_TOKEN}" \
      "${VAULT_ADDR}/v1/${VAULT_MOUNT_POINT}/data/${VAULT_CONFIG_PATH}" 2>/dev/null || echo "{}")
    PYPI_USERNAME=$(echo "${VAULT_JSON}" | python3 -c "
import json,sys
root=json.load(sys.stdin).get('data',{}).get('data',{})
d=root.get('dev',{}) or root.get('json',{}).get('dev',{})
print(d.get('repository',{}).get('pypi',{}).get('username',''))
" 2>/dev/null || echo "")
    PYPI_PASSWORD=$(echo "${VAULT_JSON}" | python3 -c "
import json,sys
root=json.load(sys.stdin).get('data',{}).get('data',{})
d=root.get('dev',{}) or root.get('json',{}).get('dev',{})
print(d.get('repository',{}).get('pypi',{}).get('password',''))
" 2>/dev/null || echo "")
  fi
fi

if [[ ${USE_LOCAL_PLATFORM_WHEELS} -eq 0 && ( -z "${PYPI_USERNAME}" || -z "${PYPI_PASSWORD}" ) ]]; then
  echo "ERROR: PYPI_USERNAME and PYPI_PASSWORD required."
  echo "  Set them as env vars or ensure Vault is accessible via env-vault."
  exit 1
fi

if [[ ${USE_LOCAL_PLATFORM_WHEELS} -eq 1 ]]; then
  cat > "${PIP_CONF}" << EOF
[global]
index-url = https://pypi.org/simple/
trusted-host = pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf generated for local platform wheel build."
else
  cat > "${PIP_CONF}" << EOF
[global]
extra-index-url = https://${PYPI_USERNAME}:${PYPI_PASSWORD}@pypi.cloud-dog.net/simple/
trusted-host = pypi.cloud-dog.net
               pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf generated with private PyPI auth."
fi

# ── CA Certificate ───────────────────────────────────────────────
if [[ -f "${CUSTOM_CA_CERT}" ]]; then
  cp "${CUSTOM_CA_CERT}" "./${GENERIC_CA_CERT}"
  CERT_ARG="--build-arg CUSTOM_CA_CERT=./${GENERIC_CA_CERT}"
fi

# ── Build ────────────────────────────────────────────────────────
DOCKER_BUILDKIT=1 docker buildx build \
  --progress=plain \
  --network=host \
  --load \
  -f Dockerfile \
  --secret id=pip_conf,src="${PIP_CONF}" \
  ${CERT_ARG} \
  --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --build-arg NO_PROXY="${NO_PROXY:-}" \
  --build-arg http_proxy="${http_proxy:-}" \
  --build-arg https_proxy="${https_proxy:-}" \
  --build-arg no_proxy="${no_proxy:-}" \
  -t "${FOLDER}/${CONTAINER}:${VERSION}" \
  . 2>&1 | tee docker-build.log

BUILD_STATUS=${PIPESTATUS[0]}

if [[ ${BUILD_STATUS} -eq 0 ]]; then
  echo "Build OK: ${FOLDER}/${CONTAINER}:${VERSION}"
  docker tag "${FOLDER}/${CONTAINER}:${VERSION}" \
    "${REGISTRY}/${FOLDER}/${CONTAINER}:${VERSION}"
  echo "Tagged: ${REGISTRY}/${FOLDER}/${CONTAINER}:${VERSION}"
else
  echo "Build FAILED — see docker-build.log"
fi

rm -f "${PIP_CONF}" "./${GENERIC_CA_CERT}"
exit ${BUILD_STATUS}
