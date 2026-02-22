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

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir \
      --trusted-host pypi.cloud-dog.net \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      .

# ── Final ────────────────────────────────────────────────────────
FROM python:3.11-slim

ARG HTTP_PROXY HTTPS_PROXY NO_PROXY http_proxy https_proxy no_proxy
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} https_proxy=${https_proxy} no_proxy=${no_proxy}

ARG CUSTOM_CA_CERT
RUN if [ -n "${CUSTOM_CA_CERT}" ] && [ -f "${CUSTOM_CA_CERT}" ]; then \
      cp "${CUSTOM_CA_CERT}" /usr/local/share/ca-certificates/custom-ca.crt && \
      update-ca-certificates; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl netcat-openbsd procps net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ ./src/
COPY defaults.yaml server_control.sh docker-entrypoint.sh healthcheck.sh ./

RUN mkdir -p /app/logs /app/data /app/.pids /app/certs && \
    chmod +x /app/docker-entrypoint.sh /app/healthcheck.sh /app/server_control.sh

RUN useradd --system --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src

EXPOSE 8686 8687

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD /app/healthcheck.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all"]
