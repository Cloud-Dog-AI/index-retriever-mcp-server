# index-retriever-mcp-server — Dockerfile (PS-91)
# Multi-stage build: proxy/CA support, private PyPI auth via BuildKit secret, non-root runtime.

# ── Builder ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ARG HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} https_proxy=${https_proxy} no_proxy=${no_proxy}

ARG CUSTOM_CA_CERT
RUN set -e; \
    if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    libxslt1-dev \
    pkg-config \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install platform packages from the approved package boundary. Read the
# BuildKit pip secret inside this RUN so credentials never become build args.
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    --mount=type=secret,id=pip_netrc,target=/root/.netrc,required=false \
    set -e; \
    INDEX_URL="$(sed -n 's/^[[:space:]]*index-url[[:space:]]*=[[:space:]]*//p' /etc/pip.conf | head -n1)" && \
    if [ -z "${INDEX_URL}" ]; then echo "ERROR: no index-url in pip.conf secret" >&2; exit 3; fi && \
    PIP_NO_INPUT=1 PIP_NO_BINARY=lxml,xmlsec pip install --no-cache-dir \
      --index-url "${INDEX_URL}" \
      --trusted-host pypi.cloud-dog.net \
      "cloud-dog-config==0.3.4" \
      cloud-dog-logging \
      "cloud-dog-cache>=0.2.0" \
      "cloud-dog-api-kit[change-stream-db]>=0.14.0" \
      "cloud-dog-idam==0.5.4" \
      cloud-dog-db \
      cloud-dog-jobs==0.4.1 \
      cloud-dog-storage==0.1.8 \
      cloud-dog-llm==0.4.1 \
      "cloud-dog-vdb>=0.5.5"

COPY REQUIREMENTS.txt pyproject.toml README.md ./
COPY src/ ./src/
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    --mount=type=secret,id=pip_netrc,target=/root/.netrc,required=false \
    set -e; \
    INDEX_URL="$(sed -n 's/^[[:space:]]*index-url[[:space:]]*=[[:space:]]*//p' /etc/pip.conf | head -n1)" && \
    if [ -z "${INDEX_URL}" ]; then echo "ERROR: no index-url in pip.conf secret" >&2; exit 3; fi && \
    PIP_NO_INPUT=1 PIP_NO_BINARY=lxml,xmlsec pip install --no-cache-dir \
      --index-url "${INDEX_URL}" \
      --trusted-host pypi.cloud-dog.net \
      -r REQUIREMENTS.txt
COPY docs/ ./docs/
COPY ui/ ./ui/
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    --mount=type=secret,id=pip_netrc,target=/root/.netrc,required=false \
    set -e; \
    INDEX_URL="$(sed -n 's/^[[:space:]]*index-url[[:space:]]*=[[:space:]]*//p' /etc/pip.conf | head -n1)" && \
    if [ -z "${INDEX_URL}" ]; then echo "ERROR: no index-url in pip.conf secret" >&2; exit 3; fi && \
    PIP_NO_INPUT=1 pip install --no-cache-dir \
      --index-url "${INDEX_URL}" \
      --trusted-host pypi.cloud-dog.net \
      hatchling && \
    PIP_NO_INPUT=1 pip install --no-cache-dir \
      --index-url "${INDEX_URL}" \
      --no-build-isolation \
      --no-deps \
      --trusted-host pypi.cloud-dog.net \
      .

# ── Final ────────────────────────────────────────────────────────
FROM python:3.12-slim
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.vendor="Cloud-Dog, Viewdeck Engineering Limited"

# W28E-1863 fix-wave-c (WSC-014): build-identity provenance. docker-build.sh passes
# SOURCE_COMMIT (git HEAD), SOURCE_BRANCH, and BUILD_DATE.
ARG SOURCE_COMMIT=unknown
ARG SOURCE_BRANCH=unknown
ARG BUILD_DATE=""
LABEL org.opencontainers.image.revision="${SOURCE_COMMIT}"
LABEL org.opencontainers.image.ref.name="${SOURCE_BRANCH}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"

ARG HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} https_proxy=${https_proxy} no_proxy=${no_proxy}

ARG CUSTOM_CA_CERT
RUN set -e; \
    if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl iproute2 netcat-openbsd procps net-tools socat \
    libxml2 \
    libxmlsec1 \
    libxmlsec1-openssl \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY REQUIREMENTS.txt pyproject.toml README.md ./
COPY src/ ./src/
COPY docs/ ./docs/
COPY ui/ ./ui/
COPY database/ ./database/
COPY defaults.yaml server_control.sh docker-entrypoint.sh healthcheck.sh ./
# W28A-F-RF-07-L3 - durable admin-state seed (users/groups/collections/api-keys).
# Token values are not in this file; only placeholder references are copied.
COPY config/ ./config/

RUN mkdir -p /app/logs /app/data /app/.pids /app/certs && \
    chmod +x /app/docker-entrypoint.sh /app/healthcheck.sh /app/server_control.sh

RUN useradd --system --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    CLOUD_DOG__INDEX__API_SERVER__HOST=0.0.0.0 \
    CLOUD_DOG__INDEX__API_SERVER__PORT=8083 \
    CLOUD_DOG__INDEX__MCP_SERVER__HOST=0.0.0.0 \
    CLOUD_DOG__INDEX__MCP_SERVER__PORT=8081 \
    CLOUD_DOG__INDEX__VDB__PROVIDER=chroma \
    CLOUD_DOG__INDEX__EMBEDDING__PROVIDER=ollama \
    CLOUD_DOG__INDEX__EMBEDDING__MODEL=nomic-embed-text \
    CLOUD_DOG__INDEX__DB__URL=sqlite+aiosqlite:////app/data/index_retriever.db

# W28E-1863 fix-wave-c (WSC-014): surface build identity to the RUNTIME so the web
# tier's _build_identity() + runtime-config.js (read config-routed via
# cloud_dog_config, RULES §1.4.1) can populate /version + GIT_COMMIT/BUILD_DATE for
# the WebUI About page. These are the keys the runtime-config already reads.
ENV CLOUD_DOG__INDEX__UI__GIT_COMMIT=${SOURCE_COMMIT} \
    CLOUD_DOG__INDEX__UI__SOURCE_BRANCH=${SOURCE_BRANCH} \
    CLOUD_DOG__INDEX__UI__BUILD_DATE=${BUILD_DATE}

EXPOSE 8080 8081 8082 8083 8686 8687

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=5 \
  CMD /app/healthcheck.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all"]
