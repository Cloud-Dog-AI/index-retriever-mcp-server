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

# index-retriever-mcp-server — Docker Build Script (PS-91 / PS-97 v1.1 §1.1.3)
# Uses BuildKit secret mount for the active package index; credentials/index
# never enter image layers.
#
# Variant selector (PS-97 v1.1 §1.1.3):
#   --variant public  (default) builds Dockerfile.public for publication.
#                     Default index is the public PyPI (pypi.org). Override the
#                     index for an approved package boundary via PYPI_URL.
#   --variant dev     builds Dockerfile (internal/dev) when present in a
#                     developer checkout. Default index is the approved internal
#                     PyPI boundary.
#
# Usage:
#   docker-build.sh [VERSION] [--variant dev|public]
#
# Env overrides still apply (PYPI_URL, PYPI_USERNAME, PYPI_PASSWORD,
# CUSTOM_CA_CERT, etc.). The --variant flag selects which Dockerfile is built.
set -euo pipefail

# ── Argument parsing ────────────────────────────────────────────
VARIANT="${PUBLICATION_BUILD_VARIANT:-public}"
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --variant)
      VARIANT="${2:-public}"
      shift 2
      ;;
    --variant=*)
      VARIANT="${1#*=}"
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]+"${POSITIONAL[@]}"}"

case "${VARIANT}" in
  dev)    DOCKERFILE="Dockerfile" ;;
  public) DOCKERFILE="Dockerfile.public" ;;
  *)
    echo "ERROR: --variant must be 'dev' or 'public' (got: ${VARIANT})" >&2
    exit 2
    ;;
esac

if [[ ! -f "${DOCKERFILE}" ]]; then
  echo "ERROR: ${DOCKERFILE} not found (variant=${VARIANT})" >&2
  exit 2
fi

VERSION="${1:-latest}"
CONTAINER="index-retriever-mcp-server"
FOLDER="cloud-dog"
REGISTRY="${REGISTRY:-}"
# Dev-variant CA path is supplied by the developer environment (INTERNAL_CA_CERT
# or CUSTOM_CA_CERT). No internal CA path is hardcoded in this published script.
CUSTOM_CA_CERT="${CUSTOM_CA_CERT:-${INTERNAL_CA_CERT:-}}"
GENERIC_CA_CERT="custom-ca.crt"
CERT_ARG=""
PIP_CONF=".pip.conf.build"
PIP_NETRC_FILE="${PIP_NETRC_FILE:-}"
PIP_NETRC_SECRET_ARGS=()

# ── Publication tag isolation (W28A-831) ──────────────────────────
# PUBLICATION_TAG_SUFFIX appends an isolation suffix (e.g. boundary-test,
# public-test) so publication test images never collide with dev/
# release tags. Empty (the default) leaves behaviour unchanged.
PUBLICATION_TAG_SUFFIX="${PUBLICATION_TAG_SUFFIX:-}"
if [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
  if [[ ! "${PUBLICATION_TAG_SUFFIX}" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    echo "ERROR: PUBLICATION_TAG_SUFFIX must match ^[a-z0-9]([a-z0-9-]*[a-z0-9])?\$ (got: '${PUBLICATION_TAG_SUFFIX}')" >&2
    exit 2
  fi
  case "${PUBLICATION_TAG_SUFFIX}" in
    latest|dev|prod|release|stable)
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
echo "Docker Build: ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG} (variant=${VARIANT}, dockerfile=${DOCKERFILE})"
echo "=========================================="

# ── PyPI Configuration ───────────────────────────────────────────
# Variant-specific default index (PS-97 §3.3 single-index; never --extra-index-url):
#   public -> pypi.org (override PYPI_URL for any other boundary index)
#   dev    -> caller-supplied approved index via INTERNAL_PYPI_URL/PYPI_URL
if [[ -n "${PYPI_URL:-}" ]]; then
  : # honour caller override
elif [[ "${VARIANT}" == "public" ]]; then
  PYPI_URL="https://pypi.org/simple/"
elif [[ -n "${INTERNAL_PYPI_URL:-}" ]]; then
  PYPI_URL="${INTERNAL_PYPI_URL}"
else
  echo "ERROR: --variant dev requires PYPI_URL or INTERNAL_PYPI_URL" >&2
  exit 2
fi
PYPI_USERNAME="${PYPI_USERNAME:-}"
PYPI_PASSWORD="${PYPI_PASSWORD:-}"
PYPI_HOST="$(python3 -c "from urllib.parse import urlsplit; print(urlsplit('${PYPI_URL}').hostname or 'pypi.org')")"

if [[ -n "${PYPI_USERNAME}" ]] || [[ -n "${PYPI_PASSWORD}" ]]; then
  echo "ERROR: use an external pip auth helper; credentials must not be embedded in index URLs" >&2
  exit 2
else
  cat > "${PIP_CONF}" << EOF
[global]
index-url = ${PYPI_URL}
trusted-host = ${PYPI_HOST}
EOF
  echo "pip.conf generated with anonymous single-index access (host=${PYPI_HOST})."
fi
chmod 600 "${PIP_CONF}"

if [[ -n "${PIP_NETRC_FILE}" ]]; then
  if [[ ! -r "${PIP_NETRC_FILE}" ]]; then
    echo "ERROR: PIP_NETRC_FILE must name a readable external auth helper" >&2
    exit 2
  fi
  PIP_NETRC_SECRET_ARGS=(--secret "id=pip_netrc,src=${PIP_NETRC_FILE}")
elif [[ "${VARIANT}" == "dev" && "${PYPI_HOST}" == "pypi.cloud-dog.net" ]]; then
  echo "ERROR: the approved private index requires an external PIP_NETRC_FILE auth helper" >&2
  exit 2
fi

# ── CA Certificate (dev/internal builds only) ────────────────────
if [[ "${VARIANT}" == "dev" && -f "${CUSTOM_CA_CERT}" ]]; then
  cp "${CUSTOM_CA_CERT}" "./${GENERIC_CA_CERT}"
  CERT_ARG="--build-arg CUSTOM_CA_CERT=./${GENERIC_CA_CERT}"
fi

# ── Build ────────────────────────────────────────────────────────
if [[ -n "${PUBLICATION_DRY_RUN:-}" ]]; then
  echo "DRY-RUN: variant=${VARIANT} dockerfile=${DOCKERFILE} index=${PYPI_URL}"
  echo "DRY-RUN: build tag = ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  if [[ "${VARIANT}" == "dev" && -n "${REGISTRY}" && -z "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "DRY-RUN: registry tag = ${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  elif [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "DRY-RUN: registry tag = (skipped — publication suffix '${PUBLICATION_TAG_SUFFIX}' set)"
  else
    echo "DRY-RUN: registry tag = (skipped)"
  fi
  exit 0
fi

# ── W28C-1719 publish-before-pin guard + build-provenance revision label (fail-closed) ──
_PBP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
NETRC="${PIP_NETRC_FILE}" "${_PBP_DIR}/scripts/publish-before-pin-guard.sh" "${_PBP_DIR}" || exit $?
_PBP_REV="$(git -C "${_PBP_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)"
# W28E-1863 fix-wave-c (WSC-014): propagate build identity to the image so the
# Dockerfile can stamp OCI labels + runtime ENV for _build_identity(). SOURCE_COMMIT
# reuses _PBP_REV so the runtime /version source_commit == the OCI revision label.
SOURCE_COMMIT="${_PBP_REV}"
SOURCE_BRANCH="$(git -C "${_PBP_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

DOCKER_BUILDKIT=1 docker buildx build \
  --label "org.opencontainers.image.revision=${_PBP_REV}" \
  --progress=plain \
  --network=host \
  --load \
  -f "${DOCKERFILE}" \
  --secret id=pip_conf,src="${PIP_CONF}" \
  "${PIP_NETRC_SECRET_ARGS[@]}" \
  ${CERT_ARG} \
  --build-arg HTTP_PROXY="${HTTP_PROXY:-}" \
  --build-arg HTTPS_PROXY="${HTTPS_PROXY:-}" \
  --build-arg NO_PROXY="${NO_PROXY:-}" \
  --build-arg http_proxy="${http_proxy:-}" \
  --build-arg https_proxy="${https_proxy:-}" \
  --build-arg no_proxy="${no_proxy:-}" \
  --build-arg SOURCE_COMMIT="${SOURCE_COMMIT}" \
  --build-arg SOURCE_BRANCH="${SOURCE_BRANCH}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  -t "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
  . 2>&1 | tee docker-build.log

BUILD_STATUS=${PIPESTATUS[0]}

if [[ ${BUILD_STATUS} -eq 0 ]]; then
  echo "Build OK: ${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG} (variant=${VARIANT})"
  if [[ "${VARIANT}" == "dev" && -n "${REGISTRY}" && -z "${PUBLICATION_TAG_SUFFIX}" ]]; then
    docker tag "${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}" \
      "${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
    echo "Tagged: ${REGISTRY}/${FOLDER}/${CONTAINER}:${EFFECTIVE_TAG}"
  elif [[ -n "${PUBLICATION_TAG_SUFFIX}" ]]; then
    echo "Publication test image (suffix=${PUBLICATION_TAG_SUFFIX}); internal registry tag skipped (W28A-831 isolation)."
  else
    echo "Public/closed-loop variant built; internal registry tag skipped (PS-97 §1.1.3)."
  fi
else
  echo "Build FAILED — see docker-build.log"
fi

exit ${BUILD_STATUS}
