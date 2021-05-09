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
from typing import Protocol, Callable, Awaitable, Any, Tuple
from aiosmtpd.smtp import AuthResult, SMTP
from email.message import EmailMessage

LocalDeliveryHandler = Callable[[EmailMessage], Awaitable[Any]]
SMTPAuthHandler = Callable[
    [SMTP, str, Any], Awaitable[AuthResult]
]  # the second parameter is method, the third is the data.
# As method "login", "plain", the data is a `LoginPassword`


class EmailQueue(Protocol):
    def get(self) -> Awaitable[Tuple[EmailMessage, int]]:
        ...

    def remove(self, index: int) -> Awaitable[None]:
        ...

    def put(self, email: EmailMessage) -> Awaitable[None]:
        ...
