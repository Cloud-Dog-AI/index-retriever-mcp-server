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


def minimal_config() -> dict[str, object]:
    return {
        "server": {"http": {"host": "0.0.0.0", "port": 8686}, "mcp": {"enabled": True, "port": 8687}},
        "auth": {
            "mode": "apikey+jwt",
            "jwt": {
                "issuer": "unit",
                "audience": "index-retriever",
                "public_keys_url": "http://localhost/jwks",
            },
        },
        "storage": {
            "db": {"url": "sqlite+aiosqlite:///data/test.db"},
            "audit": {"path": "data/audit.jsonl"},
        },
        "queue": {
            "backend": "sql",
            "database_url": "sqlite+aiosqlite:///data/test.db",
            "server_id": "test-server",
            "max_concurrency": 8,
            "per_profile_concurrency": 2,
            "default_timeout_seconds": 1800,
            "retry": {"max_attempts": 3, "backoff_seconds": 5},
            "redis": {"enabled": False, "url": ""},
        },
        "profiles": {
            "default": {
                "enabled": True,
                "vdb": {"type": "chroma", "chroma": {"mode": "local", "path": "data/chroma", "collection": "default"}},
                "embeddings": {
                    "provider": "openai_compat",
                    "openai_compat": {
                        "base_url": "http://localhost/v1",
                        "api_key": "dummy",
                        "model": "nomic-embed-text",
                        "timeout_seconds": 60,
                    },
                },
                "ingestion": {
                    "allowed_sources": ["upload", "text", "filesystem"],
                    "filesystem": {"roots": ["data"], "deny_globs": ["**/.git/**"]},
                    "max_file_mb": 50,
                    "dedupe": {"mode": "hash", "policy": "skip"},
                },
                "chunking": {"strategy": "token", "chunk_size": 5, "chunk_overlap": 1},
                "search": {"top_k_default": 10, "score_threshold": 0.0},
            }
        },
        "rbac": {"enabled": True, "default_deny": True, "roles": {"admin": ["*"], "writer": ["ingest_*"]}},
        "log": {"service_instance": "test-server", "environment": "test"},
    }
