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
from typing import Any, Dict, List, Optional

from aiosmtpd.smtp import AuthResult, LoginPassword, SMTP
from .mta import TransferAgent
from .storagehub import StorageHub
from unqlite import UnQLite


class Mailboat(object):
    """The entry of Mailboat. This class stores configuration and tools to keep other components running.

    Mailboat splits its feature units as reusable components. Current in-design components include:

    - User System (`mailboat.usrsys`)
    - Mail Transfer Agent (`mailboat.mta`)
    - Mail User Agent (in developing)
    - HTTP API Gateway (in developing)

    This class is also provided as a bridge among different components.

    .. caution:: Though many properties could be changed in runtime, be notice on the side effect!
    """

    def __init__(
        self,
        *,
        hostname: str,
        mydomains: List[str],
        database_path: str,
        smtpd_port: Optional[int] = None,
        auth_require_tls: bool = True,
    ) -> None:
        if not smtpd_port:
            smtpd_port = 8025
        self.mydomains = mydomains
        """`List[str]`. The domains which should be managed by this instance.
        For example, the doamin in email address: "random.one@foo.bar" will be seen as local mail address if "foo.bar" in mydomains,
        all messages sent to the address will be processed as local delivering."""
        self.hostname = hostname
        """`str`. The hostname of this server. Don't confuse it to `mydomains`, `hostname` is the name of this server.
        Typically it's the default domain for this instance."""
        self.database_path: str = database_path
        """`str`. The path to database. Currently it's a file path or ":mem:".
        ":mem:" tells UnQLite open database in memory."""
        self.database = UnQLite(database_path)
        """Database instance. Notice that this property may not be avaliable in future."""
        self.storage_hub = StorageHub(self.database)
        """`mailboat.StorageHub`. The references to all storages in mailboat."""
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
        """`mailboat.mta.TransferAgent`. The transfer agent for this instance."""
        self.auth_provider = AuthProvider(
            self.storage_hub.user_records, self.storage_hub.token_records
        )
        """`mailboat.usrsys.auth.AuthProvider`. The auth provider for this instance."""
        super().__init__()

    @property
    def smtpd_port(self):
        "Mail Transfer Agent's smtpd port."
        return self.transfer_agent.smtpd_port

    @property
    def auth_require_tls(self) -> bool:
        """This property defines should the SMTP Server enable the auth module for non-TLS connections."""
        return self.transfer_agent.auth_require_tls

    async def handle_smtpd_auth(
        self, server: SMTP, method: str, data: Any
    ) -> AuthResult:
        """This function is to handle authentication requests from SMTP server.

        Current supported methods:

        - login
        - plain

        Related:

        - `mailboat.mta.TransferAgent`
        """
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
        """This function is to handle local delivering (emails sent to local mail addresses), mostly from the mail transfer agent.

        Related:

        - `mailboat.mta.TransferAgent`
        """
        delivered_to = message["delivered-to"]
        raise NotImplementedError
        # TODO (rubicon): complete local delivering

    def start(self):
        """Start the engine!

        Related:

        - `mailboat.mta.TransferAgent.start`
        """
        self.transfer_agent.start()

    def stop(self):
        """Stop the mailboat instance.

        Related:

        - `mailboat.mta.TransferAgent.destory`
        """
        self.transfer_agent.destory()

    async def new_user(
        self, username: str, nickname: str, email_address: str, password: str
    ) -> UserRecord:
        """Create a new user. This method is used for programmaic uses from outside, it does access the storage directly.
        For internal uses please turn to `mailboat.StorageHub.create_user`.
        """
        user = await self.storage_hub.create_user(username, password.encode("ascii"))
        user.nickname = nickname
        user.email_address = email_address
        await self.storage_hub.user_records.update_one(
            {"profileid": user.profileid}, user
        )
        return user
