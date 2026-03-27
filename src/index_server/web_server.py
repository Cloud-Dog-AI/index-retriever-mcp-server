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

"""Web server entrypoint for SPA and legacy admin UI delivery."""

from __future__ import annotations

from index_server.api_server import build_api_app
from index_server.runtime_config import resolve_server_binding


def build_web_app() -> object:
    """Build the web server app."""
    return build_api_app()


def run_web_server() -> None:
    """Run the web server on the configured host/port."""
    app = build_web_app()
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run Web server") from exc

    binding = resolve_server_binding("web_server")
    uvicorn.run(app, host=binding.host, port=binding.port, log_level="info")


if __name__ == "__main__":
    run_web_server()
