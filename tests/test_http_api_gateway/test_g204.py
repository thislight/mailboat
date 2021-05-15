# Copyright (C) 2021 The Mailboat Contributors
#
# This file is part of Mailboat.
#
# Mailboat is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mailboat is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mailboat.  If not, see <http://www.gnu.org/licenses/>.
from mailboat import Mailboat
from ..utils import mailboat
import pytest


class TestGenerating204Handler:
    @pytest.mark.asyncio
    async def test_generate_204_will_return_204(self, mailboat: Mailboat):
        async with mailboat.http_api_gate_client() as http_cli:
            response = await http_cli.get("/generate204")
            assert response.status_code == 204
