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
from mailboat.usrsys.storage import UserRecordStorage
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class AuthRequest(object):
    username: Optional[str]
    password: Optional[str] # TODO (rubicon): use a customised type to prevent it being logged


@dataclass
class AuthAnswer(object):
    handled: bool
    success: bool
    required_second_factors: List[str]
    scope: List[str] # Note: currently it does not being used


class AuthProvider(object):
    def __init__(self, user_record_storage: UserRecordStorage) -> None:
        self.user_record_storage = user_record_storage
        super().__init__()

    async def auth(self, request: AuthRequest) -> AuthAnswer:
        if request.username and request.password:
            password_checking = await self.user_record_storage.check_user_password(request.username, request.password.encode('utf-8'))
            if password_checking:
                return AuthAnswer(handled=True, success=True, required_second_factors=[], scope=[])
            else:
                return AuthAnswer(handled=True, success=False, required_second_factors=[], scope=[])
        else:
            return AuthAnswer(handled=False, success=False, required_second_factors=[], scope=[])
