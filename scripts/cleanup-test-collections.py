#!/usr/bin/env python3
# index-retriever-mcp-server — Cleanup Test Collections
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Deletes orphaned test collections from live Chroma with confirmation.

from __future__ import annotations

import argparse
import os
import re
import sys

import chromadb

DEFAULT_PATTERNS = [
    r".*_it_chroma$",
    r".*_it_qdrant$",
    r"^[0-9a-f]{8}_default_it_chroma$",
    r"^[0-9a-f]{8}_[0-9a-f]{4}_default_it_chroma$",
]


def _compile_patterns(raw_patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in raw_patterns]


def _match_any(name: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(name) for pattern in patterns)


def _build_client(host: str, port: int, ssl: bool) -> chromadb.ClientAPI:
    token = os.getenv("CHROMA_AUTH_TOKEN", "").strip() or os.getenv(
        "CLOUD_DOG__INDEX__VDB__CHROMA_AUTH_TOKEN", ""
    ).strip()
    headers: dict[str, str] | None = None
    if token:
        headers = {"Authorization": f"Bearer {token}"}
    return chromadb.HttpClient(host=host, port=port, ssl=ssl, headers=headers)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete orphaned test collections from Chroma.")
    parser.add_argument("--host", default="chroma.cloud-dog.net")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--ssl", action="store_true", default=True)
    parser.add_argument("--no-ssl", dest="ssl", action="store_false")
    parser.add_argument("--pattern", action="append", default=[])
    parser.add_argument("--yes", action="store_true", help="Delete without interactive confirmation")
    args = parser.parse_args()

    raw_patterns = args.pattern or DEFAULT_PATTERNS
    patterns = _compile_patterns(raw_patterns)

    client = _build_client(args.host, args.port, args.ssl)
    collections = client.list_collections()
    names = sorted([item.name for item in collections])
    targets = [name for name in names if _match_any(name, patterns)]

    print(f"Chroma endpoint: {'https' if args.ssl else 'http'}://{args.host}:{args.port}")
    print(f"Total collections: {len(names)}")
    print(f"Matched test collections: {len(targets)}")
    for name in targets:
        print(f"  - {name}")

    if not targets:
        print("Nothing to delete.")
        return 0

    if not args.yes:
        answer = input("Delete all matched collections? Type 'yes' to continue: ").strip().lower()
        if answer != "yes":
            print("Cancelled. No collections deleted.")
            return 0

    deleted = 0
    failures: list[str] = []
    for name in targets:
        try:
            client.delete_collection(name)
            deleted += 1
        except Exception as exc:  # pragma: no cover - live system dependent
            failures.append(f"{name}: {exc.__class__.__name__}: {exc}")

    print(f"Deleted collections: {deleted}")
    if failures:
        print(f"Failed deletions: {len(failures)}", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
