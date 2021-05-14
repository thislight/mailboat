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
"""`AuthRequest`, `AuthAnswer` and `AuthProvider`: The authentication tools for the user system.
"""
from mailboat.usrsys.storage import TokenRecordStorage, UserRecordStorage
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class AuthRequest(object):
    """The request for authentication.

    Attributes:
        username: `Optional[str]`.
        password: `Optional[str]`.
        token: `Optional[str]`. The token string.
        appid: `Optional[str]`. The application identity.
        new_token_scope: `List[str]`. The scope of new token.
        request_token: `bool`. If request a new token.

    Typical usages:

    Verify the user with username and password:
    ````python
    AuthRequest(
        username = "...",
        password = "...",
    )
    ````

    Verify the user with username and password, and request a token:
    ````python
    AuthRequest(
        username = "...",
        password = "...",
        request_token = "...",
        new_token_scope = ["act_as_user"], # and/or any other
    )
    ````
    """

    username: Optional[str] = None
    password: Optional[
        str
    ] = None  # TODO (rubicon): use a customised type to prevent it being logged
    token: Optional[str] = None
    appid: Optional[str] = None
    new_token_scope: List[str] = field(default_factory=list)
    request_token: bool = False


@dataclass
class AuthAnswer(object):
    """The answer for authentication.

    Attributes:
        handled: `bool`. If the request can be handled correctly.
        success: `bool`. The result of the authentication.
        required_second_factors: `List[str]`. One of these second factors is required for authtication.
        scope: `List[str]`. The scope of the `token`.
        token: `Optional[str]`. The `token` string.
    """

    handled: bool
    success: bool
    required_second_factors: List[str]
    scope: List[str]  # Note: currently it does not being used
    token: Optional[str] = None


class AuthProvider(object):
    """Provide authentication to other concepts of Mailboat."""

    def __init__(
        self,
        user_record_storage: UserRecordStorage,
        token_record_storage: TokenRecordStorage,
    ) -> None:
        self.user_record_storage = user_record_storage
        self.token_record_storage = token_record_storage
        super().__init__()

    async def auth(self, request: AuthRequest) -> AuthAnswer:
        """Process an authentication request."""
        # TODO: accept token checking
        if request.username and request.password:
            password_checking = await self.user_record_storage.check_user_password(
                request.username, request.password.encode("utf-8")
            )
            if password_checking:
                token = None
                if request.request_token:
                    user_record = await self.user_record_storage.find_one(
                        {"username": request.username}
                    )
                    if user_record:
                        token = await self.token_record_storage.create_token(
                            user_record.profileid,
                            appid=request.appid,
                            scope=request.new_token_scope,
                        )  # TODO (rubicon): set apprev from latest app config (after app things done)
                return AuthAnswer(
                    handled=True,
                    success=True,
                    required_second_factors=[],
                    scope=[],
                    token=(token.token if token else None),
                )
            else:
                return AuthAnswer(
                    handled=True, success=False, required_second_factors=[], scope=[]
                )
        else:
            return AuthAnswer(
                handled=False, success=False, required_second_factors=[], scope=[]
            )
