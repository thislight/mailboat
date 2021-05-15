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
"""Simple tools to count references in memory: `Ref`.
"""
from typing import Generic, TypeVar

T = TypeVar("T")


class Ref(Generic[T]):
    """This class is provided as a tool to count references in memory."""

    def __init__(self, val: T) -> None:
        self.val = val
        """The value. Access to the value does not trigger any counting.
        """
        self.refc = 0
        """`int`. The reference counts.
        """

    def ref(self) -> T:
        """Add one to the reference counts and return the value."""
        self.refc += 1
        return self.val

    def unref(self) -> None:
        """Less the reference counts by one."""
        self.refc -= 1
