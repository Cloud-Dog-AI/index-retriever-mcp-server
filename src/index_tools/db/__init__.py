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

"""Database runtime utilities for index-retriever-mcp-server."""

from index_tools.db.models import IndexPlatformDbState
from index_tools.db.runtime import (
    PlatformDatabaseRuntime,
    database_health,
    initialise_database,
    shutdown_database,
)
from index_tools.db.structure_models import (  # noqa: F401 — register structure ORM mappers
    StructureBlockRow,
    StructureDocumentRow,
    StructureExtractorRunRow,
    StructureFigureRow,
    StructurePageRow,
    StructureRelationRow,
    StructureSectionRow,
    StructureStyleRow,
    StructureTableRow,
)

__all__ = [
    "IndexPlatformDbState",
    "PlatformDatabaseRuntime",
    "database_health",
    "initialise_database",
    "shutdown_database",
    "StructureDocumentRow",
    "StructurePageRow",
    "StructureBlockRow",
    "StructureSectionRow",
    "StructureStyleRow",
    "StructureTableRow",
    "StructureFigureRow",
    "StructureRelationRow",
    "StructureExtractorRunRow",
]
