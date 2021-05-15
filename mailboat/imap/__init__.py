from __future__ import annotations

import asyncio

from pymap.interfaces.token import TokensInterface
from mailboat.usrsys.usr import UserRecord
from mailboat.usrsys.tk import SCOPE_ACT_AS_USER, TokenRecord
import os.path
import uuid
from argparse import ArgumentParser, Namespace
from collections.abc import Awaitable, Mapping, Sequence, AsyncIterator
from contextlib import closing, asynccontextmanager
from datetime import datetime, timezone
from secrets import token_bytes
from typing import Any, Optional, Final

from pkg_resources import resource_listdir, resource_stream
from pysasl.creds import AuthenticationCredentials
from pysasl.hashing import Cleartext

from pymap.config import BackendCapability, IMAPConfig
from pymap.exceptions import (
    AuthorizationFailure,
    InvalidAuth,
    NotAllowedError,
    UserNotFound,
)
from pymap.health import HealthStatus
from pymap.interfaces.backend import BackendInterface, ServiceInterface
from pymap.interfaces.login import LoginInterface, IdentityInterface
from pymap.parsing.message import AppendMessage
from pymap.parsing.specials.flag import Flag, Recent
from pymap.token import AllTokens
from pymap.user import UserMetadata

from .filter import FilterSet
from .mailbox import Message, MailboxData, MailboxSet
from .session import BaseSession

from ..usrsys.auth import AuthProvider, AuthRequest, AuthAnswer
from .. import StorageHub

import json

__all__ = ["DictBackend", "Config"]


class DictBackend(BackendInterface):
    """Defines a backend that uses an in-memory dictionary for example usage
    and integration testing.

    """

    def __init__(self, login: Login, config: Config) -> None:
        super().__init__()
        self._login = login
        self._config = config
        self._status = HealthStatus(True)

    @property
    def login(self) -> Login:
        return self._login

    @property
    def config(self) -> Config:
        return self._config

    @property
    def status(self) -> HealthStatus:
        return self._status

    @classmethod
    def add_subparser(cls, name: str, subparsers: Any) -> ArgumentParser:
        parser = subparsers.add_parser(name, help="in-memory backend")
        parser.add_argument(
            "--demo-data", action="store_true", help="load initial demo data"
        )
        parser.add_argument(
            "--demo-user", default="demouser", metavar="VAL", help="demo user ID"
        )
        parser.add_argument(
            "--demo-password",
            default="demopass",
            metavar="VAL",
            help="demo user password",
        )
        return parser

    @classmethod
    async def init(
        cls, args: Namespace, **overrides: Any
    ) -> tuple[DictBackend, Config]:
        config = Config.from_args(args, **overrides)
        login = Login(config)
        return cls(login, config), config

    async def start(self, services: Sequence[ServiceInterface]) -> Awaitable:
        tasks = [await service.start() for service in services]
        return asyncio.gather(*tasks)


class Config(IMAPConfig):
    """The config implementation for the mailboat backend."""

    def __init__(
        self,
        args: Namespace,
        *,
        auth_provider: AuthProvider,
        storage_hub: StorageHub,
        **extra: Any
    ) -> None:
        admin_key = token_bytes()
        super().__init__(args, hash_context=Cleartext(), admin_key=admin_key, **extra)
        self.auth_provider = auth_provider
        self.storage_hub = storage_hub
        self.set_cache: dict[str, tuple[MailboxSet, FilterSet]] = {}

    @property
    def backend_capability(self) -> BackendCapability:
        return BackendCapability(idle=True, object_id=True, multi_append=True)

    @classmethod
    def parse_args(cls, args: Namespace) -> Mapping[str, Any]:
        return {**super().parse_args(args)}


class Session(BaseSession[Message]):
    """The session implementation for the dict backend."""

    def __init__(
        self, owner: str, config: Config, mailbox_set: MailboxSet, filter_set: FilterSet
    ) -> None:
        super().__init__(owner)
        self._config = config
        self._mailbox_set = mailbox_set
        self._filter_set = filter_set

    @property
    def config(self) -> Config:
        return self._config

    @property
    def mailbox_set(self) -> MailboxSet:
        return self._mailbox_set

    @property
    def filter_set(self) -> FilterSet:
        return self._filter_set


class Login(LoginInterface):
    """The login implementation for the mailboat backend."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.auth_provider = config.auth_provider
        self.user_record_storage = config.storage_hub.user_records
        self.storage_hub = config.storage_hub
        self.tokens_dict: dict[str, tuple[str, bytes]] = {}

    async def find_token_record(self, token: str) -> Optional[TokenRecord]:
        return await self.storage_hub.token_records.find_one({"token": token})

    async def find_user_record(self, profileid: str) -> Optional[UserRecord]:
        return await self.storage_hub.user_records.find_one({"profileid": profileid})

    @property
    def tokens(self) -> TokensInterface:
        raise NotImplementedError

    async def authenticate(self, credentials: AuthenticationCredentials) -> Identity:
        authcid = credentials.authcid
        token_record: Optional[TokenRecord] = None
        if credentials.authcid_type == "login-token":
            token_record = await self.find_token_record(authcid)
            if (not token_record) or (not token_record.is_avaliable()):
                raise InvalidAuth()
            user_record = await self.find_user_record(token_record.profileid)
            if not user_record:
                raise InvalidAuth()
            scope = token_record.get_scope_object()
            if not scope.is_superset_of({SCOPE_ACT_AS_USER}) or scope.is_superset_of(
                {"mail"}
            ):
                raise AuthorizationFailure()
            return Identity(user_record, token_record, self)
        elif not credentials.authcid_type:
            if not credentials.has_secret:
                raise InvalidAuth()
            result = await self.auth_provider.auth(
                AuthRequest(username=credentials.authcid, password=credentials.secret)
            )
            if (not result.handled) or (not result.success):
                raise InvalidAuth()
            user_record = await self.storage_hub.user_records.find_one(
                {"username": credentials.authcid}
            )
            if not user_record:
                raise InvalidAuth()
            new_token_record = await self.create_new_token_for_mail_access(user_record)
            return Identity(user_record, new_token_record, self)
        # No "admin-token": superusers should not be shown the others mailboxes
        raise InvalidAuth()

    async def create_new_token_for_mail_access(
        self, user_record: UserRecord, *, expiration: Optional[datetime] = None
    ) -> TokenRecord:
        new_token = await self.storage_hub.token_records.create_token(
            user_record.profileid, scope=[SCOPE_ACT_AS_USER]
        )  # TODO: use smaller scope for mail accessing
        if expiration:
            new_token.expiration = int(expiration.timestamp())
            await self.storage_hub.token_records.update_one(
                {"token": new_token}, new_token
            )
        return new_token


class Identity(IdentityInterface):
    """The identity implementation for the dict backend."""

    def __init__(
        self, user_record: UserRecord, token_record: TokenRecord, login: Login
    ) -> None:
        super().__init__()
        self.login: Final = login
        self.config: Final = login.config
        self._token_record = token_record
        self._user_record = user_record

    @property
    def name(self) -> str:
        return self._user_record.username

    async def new_token(
        self, *, expiration: Optional[datetime] = None
    ) -> Optional[str]:
        if not self._token_record.get_scope_object().is_superset_of(
            {
                SCOPE_ACT_AS_USER,
            }
        ):
            return None
        token_record = await self.login.create_new_token_for_mail_access(
            self._user_record, expiration=expiration
        )
        return token_record.token

    @asynccontextmanager
    async def new_session(self) -> AsyncIterator[Session]:
        identity = self.name
        config = self.config
        _ = await self.get()
        mailbox_set, filter_set = config.set_cache.get(identity, (None, None))
        if not mailbox_set or not filter_set:
            mailbox_set = MailboxSet()
            filter_set = FilterSet()
            # TODO： load mailboxes
            config.set_cache[identity] = (mailbox_set, filter_set)
        yield Session(identity, config, mailbox_set, filter_set)

    async def _load_demo(
        self, resource: str, mailbox_set: MailboxSet, filter_set: FilterSet
    ) -> None:
        inbox = await mailbox_set.get_mailbox("INBOX")
        await self._load_demo_mailbox(resource, "INBOX", inbox)
        mbx_names = sorted(resource_listdir(resource, "demo"))
        for name in mbx_names:
            if name == "sieve":
                await self._load_demo_sieve(resource, name, filter_set)
            elif name != "INBOX":
                await mailbox_set.add_mailbox(name)
                mbx = await mailbox_set.get_mailbox(name)
                await self._load_demo_mailbox(resource, name, mbx)

    async def _load_demo_sieve(
        self, resource: str, name: str, filter_set: FilterSet
    ) -> None:
        raise NotImplementedError
        path = os.path.join("demo", name)
        with closing(resource_stream(resource, path)) as sieve_stream:
            sieve = sieve_stream.read()
        await filter_set.put("demo", sieve)
        await filter_set.set_active("demo")

    async def _load_sieve(self, filter_set: FilterSet) -> None:
        pass  # TODO: implement sieve feature, about how-to see _load_demo_sieve
        # Sieve is for filtering mails, see https://github.com/icgood/pymap/blob/master/pymap/backend/dict/demo/sieve
        # and https://en.wikipedia.org/wiki/Sieve_(mail_filtering_language)

    async def _load_demo_mailbox(
        self, resource: str, name: str, mbx: MailboxData
    ) -> None:
        raise NotImplementedError
        path = os.path.join("demo", name)
        msg_names = sorted(resource_listdir(resource, path))
        for msg_name in msg_names:
            if msg_name == ".readonly":
                mbx._readonly = True
                continue
            elif msg_name.startswith("."):
                continue
            msg_path = os.path.join(path, msg_name)
            with closing(resource_stream(resource, msg_path)) as msg_stream:
                flags_line = msg_stream.readline()
                msg_timestamp = float(msg_stream.readline())
                msg_data = msg_stream.read()
            msg_dt = datetime.fromtimestamp(msg_timestamp, timezone.utc)
            msg_flags = {Flag(flag) for flag in flags_line.split()}
            if Recent in msg_flags:
                msg_flags.remove(Recent)
                msg_recent = True
            else:
                msg_recent = False
            append_msg = AppendMessage(msg_data, msg_dt, frozenset(msg_flags))
            await mbx.append(append_msg, recent=msg_recent)

    async def get(self) -> UserMetadata:
        data = UserMetadata(
            self.config,
            username=self._user_record.username,
            profileid=self._user_record.profileid,
        )
        if data is None:
            raise UserNotFound(self.name)
        return data

    async def set(self, data: UserMetadata) -> None:
        raise NotAllowedError()

    async def delete(self) -> None:
        raise NotAllowedError()
