"""Shared fixtures for W28A-70 QT compliance static-analysis tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return repository root."""
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    """Return source root."""
    return project_root / "src"


@pytest.fixture(scope="session")
def src_python_files(src_dir: Path) -> list[Path]:
    """Return Python files under src/."""
    return sorted(src_dir.rglob("*.py"))


@pytest.fixture(scope="session")
def test_python_files(project_root: Path) -> list[Path]:
    """Return Python files under tests/."""
    return sorted((project_root / "tests").rglob("*.py"))


@pytest.fixture(scope="session")
def env_files(project_root: Path) -> list[Path]:
    """Return all test env files."""
    return sorted((project_root / "tests").glob("env-*"))


@pytest.fixture(scope="session")
def requirements_doc(project_root: Path) -> Path:
    """Return REQUIREMENTS.md path."""
    return project_root / "REQUIREMENTS.md"


@pytest.fixture(scope="session")
def tests_doc(project_root: Path) -> Path:
    """Return TESTS.md path."""
    return project_root / "TESTS.md"


@pytest.fixture(scope="session")
def requirement_id_pattern() -> re.Pattern[str]:
    """Requirement ID matcher for FR/UC/R families used by this repo."""
    return re.compile(r"\b(?:FR-\d+(?:[A-Z])?|UC-\d+|R-[A-Z]+(?:-\d+)?)\b")


@pytest.fixture(scope="session")
def test_id_pattern() -> re.Pattern[str]:
    """Test ID matcher used in TESTS.md tables."""
    return re.compile(r"\b(?:UT|ST|IT|AT|QT|CT|PT)\d+(?:\.\d+)?[a-z]?\b")


@pytest.fixture(scope="session")
def src_text(src_python_files: list[Path]) -> str:
    """Concatenate src code text."""
    return "\n".join(_read_text(path) for path in src_python_files)


@pytest.fixture(scope="session")
def tests_text(test_python_files: list[Path]) -> str:
    """Concatenate tests code text."""
    return "\n".join(_read_text(path) for path in test_python_files)


@pytest.fixture(scope="session")
def allowlist() -> dict[str, object]:
    """Allowlist structure (kept empty; no exemptions approved for this run)."""
    return {
        "hardcoded_url_lines": set(),
        "os_environ_config_adapter_files": set(),
        "unused_env_keys": set(),
    }

