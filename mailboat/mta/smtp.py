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
"""This module contains `SMTPDHandler`, an `aiosmtpd.handlers.AsyncMessage` implementation.
"""
from aiosmtpd.handlers import AsyncMessage
from aiosmtpd.smtp import AuthResult, SMTP, LoginPassword
import aiosmtpd
from base64 import standard_b64decode
from typing import Callable, List, Awaitable, Any, Union, cast
from email.message import EmailMessage
import logging
from .protocols import SMTPAuthHandler


class SMTPDHandler(AsyncMessage):
    """
    An `aiosmtpd.handlers.AsyncMessage` implementation, which is a bridge to `mailboat.mta.TransferAgent` from `aiosmtpd`.
    ..TODO:: support OAuth2

    Related:

    - [RFC 5321: Simple Mail Transfer Protocol](https://datatracker.ietf.org/doc/html/rfc5321)
    - [aiosmtpd documentation](https://aiosmtpd.readthedocs.io/en/latest/)
    """

    __logger = logging.getLogger(__name__)

    def __init__(
        self,
        message_handler: Callable[[EmailMessage], Awaitable[Any]],
        smtp_auth_handler: SMTPAuthHandler,
    ) -> None:
        self.smtp_auth_handler = smtp_auth_handler
        """`mailboat.mta.protocols.SMTPAuthHandler`.The authentication handler."""
        self.message_handler = message_handler
        """`Callable[[EmailMessage], Awaitable[Any]]`. The email message handler."""
        super().__init__()

    async def auth_LOGIN(self, server: SMTP, args: List[str]) -> AuthResult:
        """Implementation of "login" authentication method for SMTP Protocol.

        Related:

        - [Authentication System - aiosmtpd Documentation](https://aiosmtpd.readthedocs.io/en/latest/auth.html)
        """
        username = await server.challenge_auth("Username:")
        if username == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        else:
            username = standard_b64decode(cast(bytes, username))
        password = await server.challenge_auth("Password:")
        if password == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        else:
            password = standard_b64decode(cast(bytes, password))
        return await self.smtp_auth_handler(
            server, "login", LoginPassword(cast(bytes, username), cast(bytes, password))
        )

    async def auth_PLAIN(self, server: SMTP, args: List[str]) -> AuthResult:
        """Implementation of "plain" authentication method for SMTP Protocol.

        Related:

        - [Authentication System - aiosmtpd Documentation](https://aiosmtpd.readthedocs.io/en/latest/auth.html)
        """
        words: Any
        if len(args) == 2:
            words = args[1]
        else:
            words = await server.challenge_auth("", encode_to_b64=False)
        if words == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        decoded_words = standard_b64decode(cast(bytes, words))
        parts = decoded_words.split(b"\0")
        if parts:
            if not parts[0]:
                parts.pop(0)
        if len(parts) != 2:
            return AuthResult(success=False, handled=True)
        return await self.smtp_auth_handler(
            server, "plain", LoginPassword(parts[0], parts[1])
        )

    async def handle_message(self, message: EmailMessage):
        """Handle messages from `aiosmtpd`."""
        await self.message_handler(message)
