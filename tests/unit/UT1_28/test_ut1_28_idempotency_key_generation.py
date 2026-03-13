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

# index-retriever-mcp-server — UT1.28
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests idempotency key generation determinism.

from index_tools.queue.engine import QueueEngine


def test_idempotency_key_generation() -> None:
    engine = QueueEngine()
    key1 = engine.generate_idempotency_key("default", "kb", "source")
    key2 = engine.generate_idempotency_key("default", "kb", "source")
    assert key1 == key2
