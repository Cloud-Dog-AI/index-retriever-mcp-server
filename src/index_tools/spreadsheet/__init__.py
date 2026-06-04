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

"""Spreadsheet indexing for index-retriever-mcp-server (W28E-604).

Excel/spreadsheet extraction lives in the platform package
``cloud_dog_vdb.spreadsheet`` (RULES §1.4). This package owns the service-side
SQL control plane (§14) and the orchestration that wires extraction into the
existing ingest + vector-backend path.
"""

from __future__ import annotations

from index_tools.spreadsheet.config_map import build_spreadsheet_config
from index_tools.spreadsheet.indexer import (
    SUPPORTED_SPREADSHEET_EXTENSIONS,
    SpreadsheetIndexer,
    SpreadsheetIndexResult,
    is_spreadsheet,
)

__all__ = [
    "SUPPORTED_SPREADSHEET_EXTENSIONS",
    "SpreadsheetIndexer",
    "SpreadsheetIndexResult",
    "build_spreadsheet_config",
    "is_spreadsheet",
]
