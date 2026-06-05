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
REGISTRY="${REGISTRY:-}"
CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-/usr/local/share/ca-certificates/cloud-dog.net.ca.crt}"
GENERIC_CA_CERT="custom-ca.crt"
CERT_ARG=""
PIP_CONF=".pip.conf.build"

# ── Publication tag isolation (W28A-831) ──────────────────────────
# PUBLICATION_TAG_SUFFIX appends an isolation suffix (e.g. gitea-test,
# github-test) so publication test images never collide with dev/preprod/
# release tags. Empty (the default) leaves behaviour unchanged.
PUBLICATION_TAG_SUFFIX="${PUBLICATION_TAG_SUFFIX:-}"
if [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
  if [[ ! "${PUBLICATION_TAG_SUFFIX}" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    echo "ERROR: PUBLICATION_TAG_SUFFIX must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?\$ (got: '${PUBLICATION_TAG_SUFFIX}')" >&2
    exit 2
  fi
  case "${PUBLICATION_TAG_SUFFIX}" in
    latest|dev|preprod|prod|release|stable)
      echo "ERROR: PUBLICATION_TAG_SUFFIX '${PUBLICATION_TAG_SUFFIX}' is reserved" >&2
      exit 2 ;;
  esac
  EFFECTIVE_TAG="${VERSION}-${PUBLICATION_TAG_SUFFIX}"
  echo "Publication test build: tag suffix '-${PUBLICATION_TAG_SUFFIX}' (internal registry tag will be skipped)."
else
  EFFECTIVE_TAG="${VERSION}"
fi

cleanup() {
  rm -f "${PIP_CONF}" "./${GENERIC_CA_CERT}"
}
trap cleanup EXIT

echo "=========================================="
echo "Docker Build: ${FOLDER}/${CONTAINER}:${VERSION}"
echo "=========================================="

# ── PyPI Configuration ───────────────────────────────────────────
PYPI_URL="${PYPI_URL:-https://gitea.cloud-dog.net/api/packages/Cloud-Dog-External/pypi/simple}"
PYPI_USERNAME="${PYPI_USERNAME:-}"
PYPI_PASSWORD="${PYPI_PASSWORD:-}"

if [[ -n "${PYPI_USERNAME}" ]] && [[ -n "${PYPI_PASSWORD}" ]]; then
  cat > "${PIP_CONF}" << EOF
[global]
extra-index-url = https://${PYPI_USERNAME}:${PYPI_PASSWORD}@${PYPI_URL#https://}
trusted-host = $(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'gitea.cloud-dog.net')")
               pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf generated with authenticated PyPI access."
else
  cat > "${PIP_CONF}" << EOF
[global]
extra-index-url = ${PYPI_URL}
trusted-host = $(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'gitea.cloud-dog.net')")
               pypi.org
               files.pythonhosted.org
EOF
  echo "pip.conf generated with anonymous PyPI access."
fi

# ── CA Certificate ───────────────────────────────────────────────
if [[ -f "${CUSTOM_CA_CERT}" ]]; then
  cp "${CUSTOM_CA_CERT}" "./${GENERIC_CA_CERT}"
  CERT_ARG="--build-arg CUSTOM_CA_CERT=./${GENERIC_CA_CERT}"
fi

# ── Build ────────────────────────────────────────────────────────
if [[ -n "${PUBLICATION_DRY_RUN:-}" ]]; then
  echo "DRY-RUN: build tag = ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  if [[ -n "${REGISTRY}" && -z "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "DRY-RUN: registry tag = ${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  elif [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "DRY-RUN: registry tag = (skipped — publication suffix '${PUBLICATION_TAG_SUFFIX}' set)"
  else
    echo "DRY-RUN: registry tag = (skipped; set REGISTRY to tag a registry image)"
  fi
  exit 0
fi

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
  -t "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
  . 2>&1 | tee docker-build.log

BUILD_STATUS=${PIPESTATUS[0]}

if [[ ${BUILD_STATUS} -eq 0 ]]; then
  echo "Build OK: ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  if [[ -n "${REGISTRY}" && -z "${PUBLICATION_TAG_SUFFIX}" ]]; then
    docker tag "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
      "${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
    echo "Tagged: ${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  elif [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "Publication test image (suffix=${PUBLICATION_TAG_SUFFIX}); internal registry tag skipped (W28A-831 isolation)."
  else
    echo "Registry tag skipped; set REGISTRY to tag a registry image."
  fi
else
  echo "Build FAILED — see docker-build.log"
fi

exit ${BUILD_STATUS}
