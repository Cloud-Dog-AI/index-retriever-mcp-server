# syntax=docker/dockerfile:1
# index-retriever-mcp-server — Dockerfile (PS-91)
# Multi-stage build: proxy/CA support, private PyPI auth via BuildKit secret, non-root runtime.

# ── Builder ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ARG HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} https_proxy=${https_proxy} no_proxy=${no_proxy}

ARG CUSTOM_CA_CERT
RUN if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY vendor/wheels/ ./vendor/wheels/
RUN pip install --no-cache-dir \
    ./vendor/wheels/cloud_dog_config-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_logging-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_api_kit-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_idam-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_jobs-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_db-0.1.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_llm-0.2.0-py3-none-any.whl \
    ./vendor/wheels/cloud_dog_vdb-0.4.1-py3-none-any.whl

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY ui/ ./ui/
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir \
      --trusted-host pypi.cloud-dog.net \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      .

# ── Final ────────────────────────────────────────────────────────
FROM python:3.11-slim
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.vendor="Cloud-Dog, Viewdeck Engineering Limited"

ARG HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} https_proxy=${https_proxy} no_proxy=${no_proxy}

ARG CUSTOM_CA_CERT
RUN if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl netcat-openbsd procps net-tools socat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY ui/ ./ui/
COPY database/ ./database/
COPY defaults.yaml server_control.sh docker-entrypoint.sh healthcheck.sh ./

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

EXPOSE 8080 8081 8082 8083 8686 8687

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD /app/healthcheck.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all"]
