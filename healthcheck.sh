#!/usr/bin/env bash
# index-retriever-mcp-server — Docker Health Check (PS-91)
set -euo pipefail
curl -fsS "http://127.0.0.1:${CLOUD_DOG__INDEX__API_SERVER__PORT:-8686}/health" >/dev/null
