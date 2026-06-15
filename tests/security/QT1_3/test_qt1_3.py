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

import pytest

from index_tools.tools.service import IndexService
@pytest.mark.UT
@pytest.mark.mcp
@pytest.mark.req("FR-008")


def test_non_admin_cannot_create_profile(service: IndexService) -> None:
    with pytest.raises(PermissionError):
        service.admin_profile_create("restricted", roles={"writer"})
