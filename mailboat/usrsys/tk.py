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

"""This module helps deal with tokens and scopes: `Scope` and `TokenRecord`.

Current defined scopes:

- act_as_user
- mail.read, mail.write, mail.send
- user.profile.read, user.profile.write
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Container, List, Optional, Set
from uuid import uuid4

SCOPE_ACT_AS_USER = "act_as_user"


class Scope(Container):
    """Representation for a series of permissions."""

    def __init__(self, scope: Set[str]) -> None:
        self.scope = scope
        """`Set[str]`. The original scope."""
        super().__init__()

    @staticmethod
    def match(defined_scope: str, requesting_scope: str) -> bool:
        """Check if the permission `defined_scope`'s area cover `requesting_scope`'s.

        Area is splited by `.`:
        - `s1` match `s1`
        - `s1` cover `s1.s2`
        - `s1` does not match `s2`
        """
        defined = defined_scope.split(".")
        requesting = requesting_scope.split(".")
        for p0, p1 in zip(defined, requesting):
            if p0 != p1:
                return False
        return len(defined) >= len(requesting)

    def __contains__(self, val) -> bool:
        """Check if this scope cover the `val`."""
        assert isinstance(val, str)
        for s in self.scope:
            if self.match(s, val):
                return True
        return False

    def is_superset_of(self, scope_set: Set[str]) -> bool:
        """Check if this scope is a superset of `scope_set`."""
        for s in self.scope:
            for s2 in scope_set:
                if not self.match(s, s2):
                    return False
        return True


@dataclass
class TokenRecord(object):
    """Infomation about a token.

    Attributes:
        token: `str`. The token string.
        profileid: `str`. The profile identity linked to the authenticated user.
        appid: `str` of number. Application identity. Login though username and password (not OAuth 2) is always '-1', >0 are app ids, <0 are for private.
        apprev: `str`. The reversion of the application configuration in mailboat instance. The permissions should be granted again if it is different from current configuration.
        scope: `List[str]`. The scope granted to this token.
        expiration: `Optional[int]` of unix timestamp (from UTC). After the time of the timestamp described, the token is unavaliable.
    """

    token: str
    profileid: str
    appid: str
    apprev: str
    scope: List[str]
    expiration: Optional[int] = None

    def get_scope_object(self) -> Scope:
        """Get a `Scope` object from the attribute `scope`.

        ..note:: The result is a copy from the attribute. You can use `TokenRecord.apply_new_scope` to apply the changes.
        """
        return Scope(set(self.scope))

    def apply_new_scope(self, scope: Scope):
        """Update the `scope` attribute in this record from a `Scope` object."""
        self.scope = list(scope.scope)

    @classmethod
    def new(
        cls,
        profile_id: str,
        *,
        appid: Optional[str] = None,
        apprev: Optional[str] = None,
        scope: List[str] = None,
        expiration_offest_seconds: Optional[int] = None,
    ) -> "TokenRecord":
        """Shortcut to create a new token object.
        If `appid` is `None`, set it as `'-1'`; if `apprev` is `None`, set it to empty string.
        If `scope` is empty or `None`, it will be set to `['act_as_user']`.

        ..Note:: this method just create an object , you should store it before using. Or just use `TokenRecordStorage.create_token`, which will take care of that.
        """
        tokenid = str(uuid4())
        if not appid:
            appid = "-1"
        if not apprev:
            apprev = ""
        if not scope:
            scope = [SCOPE_ACT_AS_USER]
        if expiration_offest_seconds:
            expir = int(datetime.utcnow().timestamp()) + expiration_offest_seconds
        return cls(
            token=tokenid,
            profileid=profile_id,
            appid=appid,
            apprev=apprev,
            scope=scope,
            expiration=(expir if expir else None),
        )

    def is_avaliable(self):
        """Check if the token is avaliable."""
        return self.expiration < datetime.utcnow().timestamp()
