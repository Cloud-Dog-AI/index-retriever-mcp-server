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

"""W28A-70 static checks for migration completeness."""

from __future__ import annotations

import re
from pathlib import Path


def _rel(project_root: Path, file_path: Path) -> str:
    return file_path.resolve().relative_to(project_root.resolve()).as_posix()


def test_no_yaml_safe_load_for_config(project_root: Path, src_python_files: list[Path]) -> None:
    """Config loading must not use direct yaml parsing in src/."""
    violations: list[str] = []
    for file_path in src_python_files:
        text = file_path.read_text(encoding="utf-8")
        if "yaml.safe_load(" in text or "yaml.load(" in text:
            violations.append(_rel(project_root, file_path))
    assert not violations, "Direct yaml load detected in src/:\n" + "\n".join(violations)


def test_no_raw_fastapi_instantiation(project_root: Path, src_python_files: list[Path]) -> None:
    """App creation should go through cloud_dog_api_kit."""
    pattern = re.compile(r"(?<!\w)FastAPI\(")
    violations: list[str] = []
    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "Raw FastAPI() detected:\n" + "\n".join(violations)


def test_no_bespoke_auth_hooks(project_root: Path, src_python_files: list[Path]) -> None:
    """Auth should not regress to bespoke API key/JWT handlers."""
    patterns = [
        re.compile(r"\bAPIKeyHeader\("),
        re.compile(r"def\s+verify_token\s*\("),
    ]
    violations: list[str] = []
    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        for idx, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                violations.append(f"{rel}:{idx} -> {line.strip()}")
    assert not violations, "Bespoke auth implementation detected:\n" + "\n".join(violations)


def test_cloud_dog_config_drives_loader(project_root: Path) -> None:
    """Ensure canonical loader module still imports cloud_dog_config."""
    loader = project_root / "src" / "index_tools" / "config" / "loader.py"
    text = loader.read_text(encoding="utf-8")
    assert "cloud_dog_config" in text, "Config loader must import cloud_dog_config"
    assert "load_config(" in text, "Config loader must call cloud_dog_config.load_config"


def test_os_environ_usage_is_confined_to_runtime_boundaries(
    project_root: Path,
    src_python_files: list[Path],
) -> None:
    """Environment access should remain in runtime boundary modules only."""
    allowed = {
        "src/index_server/api_server.py",
        "src/index_server/auth/middleware.py",
        "src/index_server/main.py",
        "src/index_server/mcp_server.py",
        "src/index_tools/db/runtime.py",
        "src/index_tools/tools/service.py",
        # RULES §1.4.1 BOOTSTRAP-CREDENTIAL CARVE-OUT: bootstrap.py's
        # EnvTokenResolver reads the admin-key SECRET from an operator-named env
        # var (W28A-861 publication design; the secret is never in the seed YAML
        # and cloud_dog_config cannot resolve a bare, dynamically-named env var).
        # One-shot seed-time read, same class as the VAULT_* bootstrap carve-out
        # (AGENT-BOOTSTRAP-DIRECTIVE §11). Sole os.environ read in this src/ tree;
        # see EnvTokenResolver.resolve for the inline rationale.
        "src/index_tools/bootstrap.py",
    }
    pattern = re.compile(r"os\.getenv\(|os\.environ(\[|\.get\()")
    violations: list[str] = []

    for file_path in src_python_files:
        rel = _rel(project_root, file_path)
        text = file_path.read_text(encoding="utf-8")
        if not pattern.search(text):
            continue
        if rel not in allowed:
            violations.append(rel)

    assert not violations, "os.getenv/os.environ usage outside runtime boundary modules:\n" + "\n".join(violations)
