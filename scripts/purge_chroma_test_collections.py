#!/usr/bin/env python3
# index-retriever-mcp-server — Purge Chroma Test Collections
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: One-off cleanup utility to remove orphaned test collections from live Chroma.

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any

from cloud_dog_vdb import get_vdb_client

DEFAULT_PURGE_REGEX = r"^(?:[0-9a-f]{8}|[0-9a-f]{8}_[0-9a-f]{4})_[a-z0-9]+_(?:it|st|at|qt|ct|preflight)[a-z0-9_]*$"


def _as_bool(raw: str | None, *, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _collection_name(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("name", "")).strip()
    return ""


async def _run() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tests.live_runtime import resolve_live_runtime_config

    config = resolve_live_runtime_config()
    if not config.chroma_url:
        print("ERROR: Missing CLOUD_DOG__INDEX__VDB__CHROMA_URL/CHROMA_URL.", file=sys.stderr)
        return 2

    pattern_text = os.getenv("INDEX_RETRIEVER_CHROMA_PURGE_REGEX", DEFAULT_PURGE_REGEX)
    dry_run = _as_bool(os.getenv("DRY_RUN", "true"), default=True)
    pattern = re.compile(pattern_text)

    client = get_vdb_client(
        {
            "vector_stores": {
                "default_backend": "chroma",
                "chroma": {
                    "enabled": True,
                    "base_url": config.chroma_url,
                    "auth_token": config.chroma_auth_token,
                    "timeout_seconds": 120,
                    "local_mode": False,
                },
            }
        }
    )

    rows = await client.list_collections(provider_id="chroma")
    names = sorted({name for name in (_collection_name(row) for row in rows) if name})
    targets = [name for name in names if pattern.match(name)]

    print(f"Chroma collections total: {len(names)}")
    print(f"Regex: {pattern_text}")
    print(f"Matched orphan candidates: {len(targets)}")
    for name in targets:
        print(f"  - {name}")

    if dry_run:
        print("DRY_RUN=true; no deletions performed.")
        return 0

    deleted = 0
    failed: list[str] = []
    for name in targets:
        try:
            await client.delete_collection(name, provider_id="chroma")
            deleted += 1
        except Exception as exc:  # pragma: no cover - depends on live backend responses
            failed.append(f"{name}: {exc.__class__.__name__}: {exc}")

    print(f"Deleted: {deleted}")
    if failed:
        print(f"Failed deletions: {len(failed)}", file=sys.stderr)
        for item in failed:
            print(f"  - {item}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
