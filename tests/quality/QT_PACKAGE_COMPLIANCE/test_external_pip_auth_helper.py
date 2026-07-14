# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.QT, pytest.mark.internal, pytest.mark.req("NF-001")]
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _run_dry_build(project_root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "docker-build.sh", "latest", "--variant", "dev"],
        cwd=project_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_private_dev_build_requires_external_netrc_helper() -> None:
    env = os.environ.copy()
    for name in ("PIP_NETRC_FILE", "PYPI_USERNAME", "PYPI_PASSWORD"):
        env.pop(name, None)
    env.update(PUBLICATION_DRY_RUN="1", PYPI_URL="https://pypi.cloud-dog.net/simple/")

    result = _run_dry_build(PROJECT_ROOT, env)

    assert result.returncode == 2
    assert "requires an external PIP_NETRC_FILE auth helper" in result.stderr


def test_external_netrc_is_wired_only_as_a_buildkit_secret(
    tmp_path: Path,
) -> None:
    helper = tmp_path / "pip.netrc"
    helper.write_text("machine example.invalid\n", encoding="utf-8")
    helper.chmod(0o600)
    env = os.environ.copy()
    for name in ("PYPI_USERNAME", "PYPI_PASSWORD"):
        env.pop(name, None)
    env.update(
        PUBLICATION_DRY_RUN="1",
        PYPI_URL="https://pypi.cloud-dog.net/simple/",
        PIP_NETRC_FILE=str(helper),
    )

    result = _run_dry_build(PROJECT_ROOT, env)

    assert result.returncode == 0, result.stderr
    build_script = (PROJECT_ROOT / "docker-build.sh").read_text(encoding="utf-8")
    assert '--secret "id=pip_netrc,src=${PIP_NETRC_FILE}"' in build_script
    for dockerfile_name in ("Dockerfile", "Dockerfile.public"):
        dockerfile = (PROJECT_ROOT / dockerfile_name).read_text(encoding="utf-8")
        assert "id=pip_netrc,target=/root/.netrc,required=false" in dockerfile
