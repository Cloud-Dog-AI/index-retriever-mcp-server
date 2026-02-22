# index-retriever-mcp-server — Scope Enforcement
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Filesystem and URI scope validation helpers.

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


class ScopeError(ValueError):
    """Raised when a path or URI escapes allowed scope."""


def resolve_scoped_path(allowed_roots: list[str], requested_path: str) -> Path:
    """Resolve and validate that requested_path is within configured roots."""
    candidate = Path(requested_path).resolve()
    for root in allowed_roots:
        base = Path(root).resolve()
        if candidate == base or base in candidate.parents:
            return candidate
    raise ScopeError(f"Path is outside allowed roots: {requested_path}")


def validate_uri(uri: str, allowed_schemes: set[str], allowed_hosts: set[str] | None = None) -> None:
    """Validate URI scheme and optional host allowlist."""
    parsed = urlparse(uri)
    if parsed.scheme not in allowed_schemes:
        raise ScopeError(f"Scheme is not allowed: {parsed.scheme}")
    if allowed_hosts is not None and parsed.hostname and parsed.hostname not in allowed_hosts:
        raise ScopeError(f"Host is not allowed: {parsed.hostname}")
