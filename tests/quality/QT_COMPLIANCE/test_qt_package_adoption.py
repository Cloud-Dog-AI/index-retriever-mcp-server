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

"""W28A-70 static checks for platform package adoption."""

from __future__ import annotations

import re
from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_config_package_adoption(src_text: str) -> None:
    """Verify cloud_dog_config is used for configuration loading."""
    assert "cloud_dog_config" in src_text, "Missing cloud_dog_config usage in src/"
    assert "load_dotenv(" not in src_text, "dotenv loading detected; use cloud_dog_config"
    assert "yaml.safe_load(" not in src_text, "yaml.safe_load detected; config should come from cloud_dog_config"
    assert "yaml.load(" not in src_text, "yaml.load detected; config should come from cloud_dog_config"


def test_logging_package_adoption(src_text: str) -> None:
    """Verify cloud_dog_logging is adopted and direct logger bootstrapping is absent."""
    assert "cloud_dog_logging" in src_text, "Missing cloud_dog_logging usage in src/"
    assert "logging.basicConfig(" not in src_text, "logging.basicConfig detected; use cloud_dog_logging"
    assert "logging.getLogger(" not in src_text, "logging.getLogger detected; use cloud_dog_logging wrappers"


def test_api_package_adoption(src_text: str) -> None:
    """Verify cloud_dog_api_kit adoption and no raw FastAPI app creation."""
    assert "cloud_dog_api_kit" in src_text, "Missing cloud_dog_api_kit usage"
    assert re.search(r"(?<!\w)FastAPI\(", src_text) is None, "Raw FastAPI() detected; use cloud_dog_api_kit.create_app()"


def test_idam_package_adoption(src_text: str) -> None:
    """Verify cloud_dog_idam integration is present."""
    assert "cloud_dog_idam" in src_text, "Missing cloud_dog_idam usage"
    assert "APIKeyHeader(" not in src_text, "Bespoke APIKeyHeader auth detected"
    assert re.search(r"def\s+verify_token\s*\(", src_text) is None, "Bespoke verify_token implementation detected"


def test_db_and_vdb_package_adoption(src_text: str) -> None:
    """Verify DB/VDB packages are used and direct backend clients are not."""
    assert "cloud_dog_db" in src_text, "Missing cloud_dog_db usage in src/"
    assert "cloud_dog_vdb" in src_text, "Missing cloud_dog_vdb usage in src/"
    assert "chromadb.Client(" not in src_text, "Direct chromadb.Client detected; use cloud_dog_vdb"
    assert "qdrant_client.QdrantClient(" not in src_text, "Direct qdrant client detected; use cloud_dog_vdb"


def test_pyproject_declares_required_platform_packages(project_root: Path) -> None:
    """Verify required platform packages are declared in pyproject.toml."""
    pyproject_text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    required = [
        "cloud_dog_config",
        "cloud_dog_logging",
        "cloud_dog_api_kit",
        "cloud_dog_idam",
        "cloud_dog_db",
        "cloud_dog_vdb",
    ]
    missing = [pkg for pkg in required if pkg not in pyproject_text]
    assert not missing, f"Missing required platform packages in pyproject.toml: {missing}"
