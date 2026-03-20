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

from index_tools.config.loader import merge_config_layers


def test_config_loader_precedence() -> None:
    defaults = {"server": {"http": {"port": 8686}}}
    config = {"server": {"http": {"port": 8688}}}
    dot_env = {"server": {"http": {"port": 8689}}}
    env = {"server": {"http": {"port": 8690}}}
    merged = merge_config_layers(defaults, config, dot_env, env)
    assert merged["server"]["http"]["port"] == 8690
