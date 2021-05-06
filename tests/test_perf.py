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
from typing import List
from uuid import uuid4
import pytest
from mailboat.utils.perf import (
    PERF_DATA,
    PERF_DATA_NUMBER_LIMIT,
    perf_point,
    async_perf_point,
)


class TestPerfUtils:
    def test_perf_point_can_create_perf_list_if_it_is_not_found(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @perf_point(test_str)
        def spam():
            pass

        assert test_str in PERF_DATA
        assert isinstance(PERF_DATA[test_str], List)

    def test_perf_point_can_record_perf_cell(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @perf_point(test_str)
        def spam():
            pass

        spam()
        assert isinstance(PERF_DATA[test_str], List)
        assert len(PERF_DATA[test_str]) == 1
        cell = PERF_DATA[test_str][0]
        assert cell.name == test_str
        assert isinstance(cell.t1, float)
        assert isinstance(cell.t2, float)

    def test_perf_point_can_keep_list_length_in_limit(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @perf_point(test_str)
        def spam():
            pass

        for _ in range(0, PERF_DATA_NUMBER_LIMIT + 1):
            spam()

        assert len(PERF_DATA[test_str]) == PERF_DATA_NUMBER_LIMIT

    @pytest.mark.asyncio
    async def test_async_perf_point_can_create_perf_list_if_it_is_not_found(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @async_perf_point(test_str)
        async def spam():
            pass

        assert test_str in PERF_DATA
        assert isinstance(PERF_DATA[test_str], List)

    @pytest.mark.asyncio
    async def test_async_perf_point_can_record_perf_cell(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @async_perf_point(test_str)
        async def spam():
            pass

        await spam()
        assert isinstance(PERF_DATA[test_str], List)
        assert len(PERF_DATA[test_str]) == 1
        cell = PERF_DATA[test_str][0]
        assert cell.name == test_str
        assert isinstance(cell.t1, float)
        assert isinstance(cell.t2, float)

    @pytest.mark.asyncio
    async def test_async_perf_point_can_keep_list_length_in_limit(self):
        test_str = str(uuid4())
        assert test_str not in PERF_DATA

        @async_perf_point(test_str)
        async def spam():
            pass

        for _ in range(0, PERF_DATA_NUMBER_LIMIT + 1):
            await spam()

        assert len(PERF_DATA[test_str]) == PERF_DATA_NUMBER_LIMIT
