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

from dataclasses import dataclass
from functools import wraps
from typing import Callable, Any, Dict, List
from time import perf_counter
from asyncio import Future, ensure_future

PERF_DATA: Dict[str, List["PerfCell"]] = {}

PERF_DATA_NUMBER_LIMIT = 200


@dataclass
class PerfCell(object):
    name: str
    t1: float
    t2: float

    def processing_time(self):
        return self.t2 - self.t1


def perf_point(name: str):
    if name not in PERF_DATA:
        PERF_DATA[name] = []

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            perf_list = PERF_DATA[name]
            if len(perf_list) >= PERF_DATA_NUMBER_LIMIT:
                perf_list.pop(0)
            t1 = perf_counter()
            val = f(*args, **kwargs)
            t2 = perf_counter()
            perf_list.append(PerfCell(name, t1, t2))
            return val

        return wrapper

    return decorator


def async_perf_point(name: str):
    if name not in PERF_DATA:
        PERF_DATA[name] = []

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Future[Any]:
            perf_list = PERF_DATA[name]
            if len(perf_list) >= PERF_DATA_NUMBER_LIMIT:
                perf_list.pop(0)
            t1 = perf_counter()
            fut = ensure_future(f(*args, **kwargs))

            @fut.add_done_callback
            def perf_callback(fut):
                t2 = perf_counter()
                perf_list.append(PerfCell(name, t1, t2))

            return fut

        return wrapper

    return decorator
