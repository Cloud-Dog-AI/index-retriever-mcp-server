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

# index-retriever-mcp-server — UT1.42
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Google Drive connector reference parsing and error mapping.

from __future__ import annotations

import pytest

from index_tools.connectors.gdrive import map_http_error, resolve


def test_connector_gdrive_resolve_raw_id() -> None:
    plan = resolve("1AbCdEfGhIjKlMnOpQrStUvWxYz")
    assert plan.source_type == "gdrive"
    assert plan.metadata["file_id"] == "1AbCdEfGhIjKlMnOpQrStUvWxYz"
    assert plan.metadata["download_url"].endswith("1AbCdEfGhIjKlMnOpQrStUvWxYz?alt=media")


def test_connector_gdrive_resolve_shared_link() -> None:
    plan = resolve("https://drive.google.com/file/d/1ABCDEF/view?usp=sharing")
    assert plan.location == "1ABCDEF"
    assert plan.metadata["file_id"] == "1ABCDEF"


def test_connector_gdrive_resolve_query_link() -> None:
    plan = resolve("https://drive.google.com/open?id=2XYZ")
    assert plan.location == "2XYZ"
    assert plan.metadata["file_id"] == "2XYZ"


def test_connector_gdrive_resolve_requires_file_id() -> None:
    with pytest.raises(ValueError, match="Google Drive file ID is required"):
        _ = resolve("https://example.com/not-drive")


def test_connector_gdrive_error_mapping() -> None:
    auth_error = map_http_error(403, "fid-1")
    missing_error = map_http_error(404, "fid-2")
    transient_error = map_http_error(503, "fid-3")

    assert isinstance(auth_error, PermissionError)
    assert isinstance(missing_error, FileNotFoundError)
    assert isinstance(transient_error, ConnectionError)
