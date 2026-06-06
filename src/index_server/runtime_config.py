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

"""Runtime config helpers for server host/port resolution."""

from __future__ import annotations

from dataclasses import dataclass

from index_tools.config.loader import load_runtime_config


@dataclass(frozen=True, slots=True)
class ServerBinding:
    """Resolved host/port binding for a runtime server."""

    host: str
    port: int


_KNOWN_SERVERS = frozenset({"api_server", "web_server", "mcp_server", "a2a_server"})


def resolve_server_binding(server_name: str) -> ServerBinding:
    """Resolve host/port from the canonical cloud_dog_config precedence chain."""
    if server_name not in _KNOWN_SERVERS:
        raise KeyError(f"Unknown server binding: {server_name}")

    runtime_config = load_runtime_config(
        unresolved_policy="strict",
    )
    endpoint = getattr(runtime_config, server_name)
    return ServerBinding(host=endpoint.host, port=int(endpoint.port))
