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

"""This library helps deal with tokens and scopes.
Currently usrsys defines these scopes:

- act_as_user
- mail.read, mail.write, mail.send
- user.profile.{read, write}
"""

from dataclasses import dataclass
from typing import Container, List, Optional, Set
from uuid import uuid4

SCOPE_ACT_AS_USER = "act_as_user"


class Scope(Container):
    def __init__(self, scope: Set[str]) -> None:
        self.scope = scope
        super().__init__()

    @staticmethod
    def match(defined_scope: str, requesting_scope: str) -> bool:
        defined = defined_scope.split(".")
        requesting = requesting_scope.split(".")
        for p0, p1 in zip(defined, requesting):
            if p0 != p1:
                return False
        return len(defined) >= len(requesting)

    def __contains__(self, val) -> bool:
        assert isinstance(val, str)
        for s in self.scope:
            if self.match(s, val):
                return True
        return False

    def is_superset_of(self, scope_set: Set[str]) -> bool:
        for s in self.scope:
            for s2 in scope_set:
                if not self.match(s, s2):
                    return False
        return True


@dataclass
class TokenRecord(object):
    token: str
    profileid: str
    appid: str  # login though username and password (not OAuth 2) is always '-1', >0 are app ids, <0 are for private
    apprev: str
    scope: List[str]

    def get_scope_object(self) -> Scope:
        return Scope(set(self.scope))

    def apply_new_scope(self, scope: Scope):
        self.scope = list(scope.scope)

    @classmethod
    def new(
        cls,
        profile_id: str,
        *,
        appid: Optional[str] = None,
        apprev: Optional[str] = None,
        scope: List[str]
    ) -> "TokenRecord":
        """Shortcut to create a new token object.
        If `appid` is `None`, set it as `'-1'`; if `apprev` is `None`, set it to empty string.
        If `scope` is empty or `None`, it will be set to `['act_as_user']`.

        Note: this method just create an object , you should store it before using. Or just use `TokenRecordStorage.create_token`.
        """
        tokenid = str(uuid4())
        if not appid:
            appid = "-1"
        if not apprev:
            apprev = ""
        if not scope:
            scope = [SCOPE_ACT_AS_USER]
        return cls(
            token=tokenid, profileid=profile_id, appid=appid, apprev=apprev, scope=scope
        )
