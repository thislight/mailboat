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

from email.message import EmailMessage
from .usrsys.usr import UserRecord
from .usrsys.auth import AuthProvider, AuthRequest
from typing import Any, Dict, List, Optional, Tuple
from .apigate import HTTPAPIGateway

from aiosmtpd.smtp import AuthResult, LoginPassword, SMTP
from .mta import TransferAgent
from . import StorageHub
from unqlite import UnQLite

import httpx


class Mailboat(object):
    def __init__(
        self,
        *,
        hostname: str,
        mydomains: List[str],
        database_path: str,
        smtpd_port: Optional[int] = None,
        auth_require_tls: bool = True,
        http_api_gate_binds: List[Tuple[Optional[str], int]] = None,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        if not smtpd_port:
            smtpd_port = 8025
        self.mydomains = mydomains
        self.hostname = hostname
        self.database_path = database_path
        self.database = UnQLite(database_path)
        self.storage_hub = StorageHub(self.database)
        self.transfer_agent = TransferAgent(
            mydomains=mydomains,
            local_delivery_handler=self.handle_local_delivering,
            database=self.storage_hub.database,
            smtpd_auth_handler=self.handle_smtpd_auth,
            hostname=self.hostname,
            self_name="transfer_agent.{}".format(self.hostname),
            smtpd_port=smtpd_port,
            auth_require_tls=auth_require_tls,
        )
        self.auth_provider = AuthProvider(
            self.storage_hub.user_records, self.storage_hub.token_records
        )
        self.http_api_gate = HTTPAPIGateway(
            self.storage_hub,
            http_binds=http_api_gate_binds if http_api_gate_binds else [],
        )
        super().__init__()

    @property
    def smtpd_port(self):
        return self.transfer_agent.smtpd_port

    @property
    def auth_require_tls(self) -> bool:
        return self.transfer_agent.auth_require_tls

    async def handle_smtpd_auth(
        self, server: SMTP, method: str, data: Any
    ) -> AuthResult:
        if method == "login" or method == "plain":
            assert isinstance(data, LoginPassword)
            username: bytes = data.login
            password: bytes = data.password
            auth_request = AuthRequest(
                username=username.decode("utf-8"), password=password.decode("utf-8")
            )  # TODO (rubicon): support the other charsets
            result = await self.auth_provider.auth(auth_request)
            return AuthResult(success=result.success, handled=result.handled)
        else:
            return AuthResult(success=False, handled=False)

    async def handle_local_delivering(self, message: EmailMessage):
        delivered_to = message["delivered-to"]
        raise NotImplementedError
        # TODO (rubicon): complete local delivering

    async def start(self):
        self.transfer_agent.start()
        await self.http_api_gate.start()

    async def stop(self):
        self.transfer_agent.destory()
        await self.http_api_gate.stop()

    async def new_user(
        self, username: str, nickname: str, email_address: str, password: str
    ) -> UserRecord:
        user = await self.storage_hub.create_user(username, password.encode("ascii"))
        user.nickname = nickname
        user.email_address = email_address
        await self.storage_hub.user_records.update_one(
            {"profileid": user.profileid}, user
        )
        return user

    def http_api_gate_client(self) -> httpx.AsyncClient:
        return self.http_api_gate.http_client()
