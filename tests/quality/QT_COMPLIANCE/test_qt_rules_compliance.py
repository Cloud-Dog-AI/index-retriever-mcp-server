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

"""W28A-70 static checks for RULES.md compliance (RC-01 .. RC-10)."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path


def _rel(project_root: Path, file_path: Path) -> str:
    return file_path.resolve().relative_to(project_root.resolve()).as_posix()


def _iter_code_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        lines.append((idx, line))
    return lines


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_rc01_no_hardcoded_urls_or_loopback(
    project_root: Path,
    src_python_files: list[Path],
    allowlist: dict[str, object],
) -> None:
    """RC-01: detect hardcoded URL/loopback/path literals in src/."""
    url_or_path_patterns = [
        re.compile(r"https?://[^\s\"']+"),
        re.compile(r"\blocalhost\b", re.IGNORECASE),
        re.compile(r"\b127\.0\.0\.1\b"),
        re.compile(r"/tmp/"),
        re.compile(r"/var/"),
    ]
    allowed = set(allowlist["hardcoded_url_lines"])
    violations: list[str] = []

    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in _iter_code_lines(file_path):
            if any(pattern.search(line) for pattern in url_or_path_patterns):
                marker = f"{rel}:{idx}"
                if marker in allowed:
                    continue
                violations.append(f"{marker} -> {line.strip()}")

    assert not violations, "RC-01 hardcoded URL/loopback/path findings:\n" + "\n".join(violations)


def test_rc02_no_hardcoded_credentials(project_root: Path, src_python_files: list[Path]) -> None:
    """RC-02: no hardcoded credential literals."""
    cred_re = re.compile(r"\b(password|token|api_key|secret)\b\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE)
    violations: list[str] = []
    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in _iter_code_lines(file_path):
            if cred_re.search(line):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "RC-02 hardcoded credential assignments:\n" + "\n".join(violations)


def test_rc03_external_imports_not_scattered(project_root: Path, src_python_files: list[Path]) -> None:
    """RC-03: high-risk external libs should not fan out across many modules."""
    external_libs = ("requests", "httpx", "smtplib", "chromadb", "openai", "ollama", "qdrant_client")
    import_sites: dict[str, set[str]] = defaultdict(set)

    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        text = file_path.read_text(encoding="utf-8")
        for lib in external_libs:
            if re.search(rf"^\s*(?:import|from)\s+{re.escape(lib)}\b", text, re.MULTILINE):
                import_sites[lib].add(rel)

    violations = []
    for lib, sites in sorted(import_sites.items()):
        if len(sites) > 1:
            violations.append(f"{lib}: {sorted(sites)}")

    assert not violations, "RC-03 external imports spread across modules:\n" + "\n".join(violations)


def test_rc04_headers_and_docstring_coverage(project_root: Path, src_python_files: list[Path]) -> None:
    """RC-04: ensure file headers and >=80% public symbol docstrings."""
    missing_headers: list[str] = []
    total_public = 0
    documented_public = 0
    missing_docstrings: list[str] = []

    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        first_lines = file_path.read_text(encoding="utf-8").splitlines()[:10]
        if not any(line.strip().startswith("#") or line.strip().startswith('"""') for line in first_lines):
            missing_headers.append(rel)

        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                total_public += 1
                if ast.get_docstring(node):
                    documented_public += 1
                else:
                    missing_docstrings.append(f"{rel}:{node.lineno}:{node.name}")

    ratio = 100.0 if total_public == 0 else (documented_public / total_public) * 100
    assert not missing_headers, "RC-04 missing file headers:\n" + "\n".join(missing_headers)
    assert ratio >= 80.0, (
        f"RC-04 public docstring coverage below threshold: {ratio:.2f}% (required >= 80.0%).\n"
        + "\n".join(missing_docstrings[:200])
    )


def test_rc05_no_mocking_patterns_in_it_at(project_root: Path, test_python_files: list[Path]) -> None:
    """RC-05: IT/AT must not use local_mode=True or mock transport shortcuts."""
    pattern = re.compile(r"MagicMock|MockTransport|local_mode\s*=\s*True")
    violations: list[str] = []
    for file_path in test_python_files:
        rel = _rel(project_root, file_path)
        if "/integration/" not in rel and "/application/" not in rel:
            continue
        for idx, line in _iter_code_lines(file_path):
            if pattern.search(line):
                violations.append(f"{rel}:{idx} -> {line.strip()}")

    assert not violations, "RC-05 mock/local-mode usage in IT/AT:\n" + "\n".join(violations)


def test_rc06_no_pytest_skip_in_it_at(project_root: Path, test_python_files: list[Path]) -> None:
    """RC-06: IT/AT must fail closed, not skip."""
    violations: list[str] = []
    for file_path in test_python_files:
        rel = _rel(project_root, file_path)
        if "/integration/" not in rel and "/application/" not in rel:
            continue
        for idx, line in _iter_code_lines(file_path):
            if "pytest.skip(" in line:
                violations.append(f"{rel}:{idx} -> {line.strip()}")

    assert not violations, "RC-06 pytest.skip found in IT/AT:\n" + "\n".join(violations)


def test_rc07_no_raw_vault_template_in_py_tests(project_root: Path, test_python_files: list[Path]) -> None:
    """RC-07: fixture/test code should not hardcode Vault expression templates."""
    violations: list[str] = []
    for file_path in test_python_files:
        rel = _rel(project_root, file_path)
        if rel.startswith("tests/quality/QT_COMPLIANCE/"):
            continue
        if not rel.startswith("tests/"):
            continue
        for idx, line in _iter_code_lines(file_path):
            if "${vault.dev." in line:
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "RC-07 raw vault templates found in test code:\n" + "\n".join(violations)


def test_rc08_tier_env_files_are_connected_to_runtime(
    env_files: list[Path],
    tests_text: str,
    src_text: str,
) -> None:
    """RC-08: each core tier env file should expose at least one consumed variable."""
    required_tiers = {"env-UT", "env-ST", "env-IT", "env-AT", "env-QT"}
    env_map = {path.name: _parse_env(path) for path in env_files}
    missing_files = sorted(required_tiers - set(env_map))
    assert not missing_files, f"RC-08 missing required env files: {missing_files}"

    combined = f"{tests_text}\n{src_text}"
    disconnected: list[str] = []
    for env_name in sorted(required_tiers):
        keys = list(env_map[env_name].keys())
        consumed = [key for key in keys if key in combined]
        if not consumed:
            disconnected.append(env_name)
    assert not disconnected, "RC-08 disconnected tier env files (no consumed keys):\n" + "\n".join(disconnected)


def test_rc09_no_stub_placeholders(project_root: Path, src_python_files: list[Path]) -> None:
    """RC-09: implemented requirements should not be left as stubs."""
    patterns = [
        re.compile(r"NotImplementedError\("),
        re.compile(r"TODO:\s*implement", re.IGNORECASE),
    ]
    violations: list[str] = []
    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in _iter_code_lines(file_path):
            if any(pattern.search(line) for pattern in patterns):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "RC-09 stub/placeholder implementation markers:\n" + "\n".join(violations)


def test_rc10_no_american_spelling_in_user_facing_errors(project_root: Path, src_python_files: list[Path]) -> None:
    """RC-10: user-facing strings should prefer project spelling conventions."""
    american = re.compile(r"\b(authoriz|optimiz|color|behavior)\w*\b", re.IGNORECASE)
    violations: list[str] = []
    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in _iter_code_lines(file_path):
            if "raise " not in line and "detail=" not in line and "message=" not in line:
                continue
            if american.search(line):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "RC-10 American spelling in user-facing errors:\n" + "\n".join(violations)
