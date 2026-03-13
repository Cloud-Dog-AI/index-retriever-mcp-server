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
