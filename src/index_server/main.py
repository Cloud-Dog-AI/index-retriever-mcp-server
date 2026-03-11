# index-retriever-mcp-server — Main Entrypoint
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Runtime entrypoint for index retriever server components.

from __future__ import annotations

import os

from index_server.api_server import build_api_app


def main() -> object:
    """Bootstrap the API app. Only bootstrap env access is allowed here."""
    _ = os.getenv("CLOUD_DOG_ENV_FILES", "")
    return build_api_app()


if __name__ == "__main__":
    main()
