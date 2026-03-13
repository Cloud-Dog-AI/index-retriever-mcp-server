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

# index-retriever-mcp-server — HTTP Connector
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: HTTP URI resolver for optional web ingestion.

from __future__ import annotations

from urllib.parse import urlparse

from index_tools.connectors.models import FetchPlan


def resolve(uri: str) -> FetchPlan:
    """Execute resolve."""
    parsed = urlparse(uri)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Invalid HTTP URI")
    return FetchPlan(source_type="http", location=uri, metadata={"host": parsed.netloc})
