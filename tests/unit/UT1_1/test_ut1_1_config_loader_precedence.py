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

import os

from index_tools.config.loader import merge_config_layers


def test_config_loader_precedence() -> None:
    base_port = int(os.environ.get("CLOUD_DOG__API_SERVER__PORT", "8074"))
    defaults = {"api_server": {"port": base_port}}
    config = {"api_server": {"port": base_port + 1}}
    dot_env = {"api_server": {"port": base_port + 2}}
    env = {"api_server": {"port": base_port + 3}}
    merged = merge_config_layers(defaults, config, dot_env, env)
    assert merged["api_server"]["port"] == base_port + 3
