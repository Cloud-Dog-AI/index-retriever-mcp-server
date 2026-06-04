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

"""Canonical document-structure intelligence subsystem (design brief W28E-603, Phase 1).

Public surface: the canonical model, the transport-neutral :class:`StructureService`, and the
``cloud_dog_db``-routed :class:`StructureRepository`.
"""

from index_tools.structure.models import (
    SCHEMA_VERSION,
    BlockType,
    SectionType,
    StructureBlock,
    StructureBundle,
    StructureDocument,
    StructureExtractorRun,
    StructureFigure,
    StructurePage,
    StructureRelation,
    StructureSection,
    StructureStatus,
    StructureStyle,
    StructureTable,
)
from index_tools.structure.repository import StructureRepository
from index_tools.structure.service import StructureService

__all__ = [
    "SCHEMA_VERSION",
    "BlockType",
    "SectionType",
    "StructureStatus",
    "StructureDocument",
    "StructurePage",
    "StructureBlock",
    "StructureSection",
    "StructureStyle",
    "StructureTable",
    "StructureFigure",
    "StructureRelation",
    "StructureExtractorRun",
    "StructureBundle",
    "StructureRepository",
    "StructureService",
]
