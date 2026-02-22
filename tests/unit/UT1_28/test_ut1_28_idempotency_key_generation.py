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
