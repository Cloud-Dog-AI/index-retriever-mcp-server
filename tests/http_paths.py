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

from __future__ import annotations

import os


def _normalise_base_path(raw: str, default: str) -> str:
    value = raw.strip() or default
    if not value.startswith("/"):
        value = f"/{value}"
    if value != "/" and value.endswith("/"):
        value = value[:-1]
    return value


def api_base_path() -> str:
    return _normalise_base_path(os.environ.get("TEST_API_BASE_PATH", ""), "/api/v1")


def mcp_base_path() -> str:
    return _normalise_base_path(os.environ.get("TEST_MCP_BASE_PATH", ""), "/mcp")


def a2a_base_path() -> str:
    return _normalise_base_path(os.environ.get("TEST_A2A_BASE_PATH", ""), "/a2a")


def api_tools_path(tool_name: str | None = None) -> str:
    base = f"{api_base_path()}/tools"
    if tool_name is None:
        return base
    return f"{base}/{tool_name}"


def mcp_tools_path(tool_name: str | None = None) -> str:
    base = f"{mcp_base_path()}/tools"
    if tool_name is None:
        return base
    return f"{base}/{tool_name}"


def a2a_health_path() -> str:
    return f"{a2a_base_path()}/health"
