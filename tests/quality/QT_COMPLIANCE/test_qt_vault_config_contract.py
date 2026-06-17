# @pytest.mark.QT
# @pytest.mark.internal
# @pytest.mark.probe
# PS-REQ-TEST-TRACE marker anchor for structural conformance.

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

"""W28A-70 static checks for vault/config/secret contract."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_env_map(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in _read(path).splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _looks_like_secret_literal(value: str) -> bool:
    text = value.strip().strip("'").strip('"')
    if not text:
        return False
    if text.startswith("${"):
        return False
    known_safe = {"test-api-key", "12345678", "dummy"}
    if text in known_safe:
        return False
    if text.lower().startswith(("http://", "https://", "sqlite+", "postgresql+", "mysql+", "redis://", "file://")):
        return False
    return bool(re.search(r"[A-Za-z0-9_\-]{8,}", text))


def test_defaults_yaml_exists(project_root: Path) -> None:
    """defaults.yaml must exist."""
    assert (project_root / "defaults.yaml").exists(), "defaults.yaml is required"


def test_defaults_yaml_has_no_literal_secrets(project_root: Path) -> None:
    """defaults.yaml must not contain literal credential values."""
    text = _read(project_root / "defaults.yaml")
    patterns = [
        re.compile(r"(?i)\b(glpat-|hvs\.|sk-or-v1-)\b"),
        re.compile(r"(?i)\b(password|token|api[_-]?key|secret)\b\s*:\s*['\"]?[^\s#'\"]+"),
    ]
    violations = [pattern.pattern for pattern in patterns if pattern.search(text)]
    # Interpolated values (${...}) are allowed placeholders and should not trip.
    if violations and "${" in text:
        interpolated_only = []
        for line in text.splitlines():
            if "${" not in line:
                interpolated_only.append(line)
        non_interpolated = "\n".join(interpolated_only)
        violations = [pattern.pattern for pattern in patterns if pattern.search(non_interpolated)]
    assert not violations, f"Potential literal secrets detected in defaults.yaml: {violations}"


def test_env_files_have_valid_vault_expression_syntax(env_files: list[Path]) -> None:
    """Vault expressions should use ${vault.dev.*} syntax where present."""
    pattern = re.compile(r"^\$\{vault\.dev\.[^}]+\}$")
    violations: list[str] = []
    seen_vault_expr = 0
    for env_path in env_files:
        for key, value in _load_env_map(env_path).items():
            if "${vault.dev." not in value:
                continue
            seen_vault_expr += 1
            if not pattern.match(value):
                violations.append(f"{env_path.as_posix()}::{key}={value}")
    assert seen_vault_expr > 0, "No vault expressions found in tests/env-*"
    assert not violations, "Invalid vault expression syntax:\n" + "\n".join(violations)


def test_sensitive_env_keys_use_vault_or_explicit_test_values(env_files: list[Path]) -> None:
    """Sensitive keys in env files should use vault expressions or approved test values."""
    sensitive_key = re.compile(r"(?i)(PASSWORD|TOKEN|SECRET|USERNAME|API_KEY)")
    allowed_test_prefixes = ("TEST_",)
    violations: list[str] = []

    for env_path in env_files:
        values = _load_env_map(env_path)
        for key, value in values.items():
            if not sensitive_key.search(key):
                continue
            cleaned = value.strip()
            if key.startswith(allowed_test_prefixes):
                continue
            if cleaned.startswith("${vault.dev."):
                continue
            if cleaned in {"", "test-api-key", "12345678", "dummy"}:
                continue
            if "AUTH__API_KEYS" in key and "test-api-key" in cleaned:
                continue
            violations.append(f"{env_path.as_posix()}::{key}={value}")

    assert not violations, "Sensitive env keys without vault/test-safe value:\n" + "\n".join(violations)


def test_no_literal_secrets_in_source(src_python_files: list[Path], project_root: Path) -> None:
    """Source code should not embed secrets."""
    patterns = [
        re.compile(r"(?i)\b(glpat-[a-z0-9]{10,}|hvs\.[a-z0-9_-]{10,}|sk-or-v1-[a-z0-9_-]{10,})\b"),
        re.compile(r"(?i)\b(password|token|api[_-]?key|secret)\b\s*=\s*['\"][^'\"]{12,}['\"]"),
    ]
    violations: list[str] = []
    for file_path in src_python_files:
        rel = file_path.resolve().relative_to(project_root.resolve()).as_posix()
        for idx, line in enumerate(_read(file_path).splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if any(pattern.search(line) for pattern in patterns):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "Potential literal secrets in src/:\n" + "\n".join(violations)


def test_env_tiers_exist(project_root: Path) -> None:
    """Core test tier env files must exist."""
    required = ["env-UT", "env-ST", "env-IT", "env-AT", "env-QT"]
    missing = [name for name in required if not (project_root / "tests" / name).exists()]
    assert not missing, f"Missing required tier env files: {missing}"


def test_env_files_avoid_obvious_literal_secret_values(env_files: list[Path]) -> None:
    """Detect obvious non-vault secret-like values in env files."""
    sensitive_key = re.compile(r"(?i)(PASSWORD|TOKEN|SECRET|API_KEY)")
    violations: list[str] = []
    for env_path in env_files:
        for key, value in _load_env_map(env_path).items():
            if not sensitive_key.search(key):
                continue
            if "AUTH__API_KEYS" in key and "test-api-key" in value:
                continue
            if _looks_like_secret_literal(value):
                violations.append(f"{env_path.as_posix()}::{key}={value}")
    assert not violations, "Literal secret-like values found in env files:\n" + "\n".join(violations)
