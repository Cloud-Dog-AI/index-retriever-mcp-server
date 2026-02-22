# index-retriever-mcp-server — Unit Test Helpers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared helper data for unit tests.

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
    }
