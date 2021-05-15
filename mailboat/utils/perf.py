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
"""Tools to measure performance at runtime.
"""

from dataclasses import dataclass
from functools import wraps
from typing import Callable, Any, Dict, List
from time import perf_counter
from asyncio import Future, ensure_future

PERF_DATA: Dict[str, List["PerfCell"]] = {}
"""All performance data. The key is the name of perf point.
"""

PERF_DATA_NUMBER_LIMIT = 200
"""The high mark for one perf point.
"""


@dataclass
class PerfCell(object):
    """Infomation about one-run.

    Attributes:
        name: `str`. The name of the perf point.
        t1: `float`. The start time of the run.
        t2: `float`. The end time of the run.
    """

    name: str
    t1: float
    t2: float

    def processing_time(self):
        """Return the used time of the run."""
        return self.t2 - self.t1


def perf_point(name: str):
    """A decorator which measuring performance of synchrounous functions.

    Typical usage:

    ````python
    @perf_point("test")
    def spam():
        pass
    ````

    ..note:: You can access the data in `PERF_DATA`.
    """
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
    """A decorator which measuring performance of asynchrounous functions.

    Typical usage:

    ````python
    @async_perf_point("test")
    async def spam():
        pass
    ````

    ````python
    @async_perf_point("test")
    def spam() -> Awaitable[Any]:
        ...
    ````

    ..note:: You can access the data in `PERF_DATA`.

    ..tips:: The function will always be run.
        This decorator will convert use `ensure_future` on the function result.
        That means the function will be always run when the function called, even the function is a coroutine.
        And the wrapped function will always return `Future`.
    """
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
