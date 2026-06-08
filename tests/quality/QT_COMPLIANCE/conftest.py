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
    """Allowlist structure for legitimate runtime patterns."""
    return {
        "hardcoded_url_lines": {
            # web_server.py: _normalise_api_host() converts wildcard bind
            # addresses (0.0.0.0, ::) into a routable loopback for the
            # internal reverse-proxy bridge.  The http:// URLs are built
            # from config-resolved host:port, not hardcoded endpoints.
            # (Line numbers track _normalise_api_host + the three base-URL builders.)
            "src/index_server/web_server.py:86",
            "src/index_server/web_server.py:87",
            "src/index_server/web_server.py:96",
            "src/index_server/web_server.py:151",
            "src/index_server/web_server.py:152",
        },
        "os_environ_config_adapter_files": set(),
        "unused_env_keys": set(),
    }
