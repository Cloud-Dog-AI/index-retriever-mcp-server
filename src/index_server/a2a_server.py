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

"""A2A server entrypoint for the authenticated A2A surface."""

from __future__ import annotations

from index_server.api_server import build_api_app
from index_server.runtime_config import resolve_server_binding


def build_a2a_app() -> object:
    """Build the A2A server app."""
    return build_api_app(surface_name="a2a_server")


def run_a2a_server() -> None:
    """Run the A2A server on the configured host/port."""
    app = build_a2a_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run A2A server") from exc

    binding = resolve_server_binding("a2a_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_a2a_server()
# W28A-565 fix 1775032326
