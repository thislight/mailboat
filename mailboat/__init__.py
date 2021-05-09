from dataclasses import dataclass
from typing import Optional
from mailboat.usrsys.usr import MAILBOX_DEFAULT_SETTING, MailBoxRecord, UserRecord
from .usrsys.mailbox import MailBox
from .mailstore import MailStore
from .usrsys.storage import (
    MailBoxRecordStorage,
    MailRecordStorage,
    ProfileRecordStorage,
    UserRecordStorage,
    TokenRecordStorage,
)
from unqlite import UnQLite
from .utils.storage import CommonStorage, UnQLiteStorage


class StorageHub(object):
    """All storages about mailboat"""

    def __init__(self, database: UnQLite) -> None:
        self.database = database
        super().__init__()

    def get_common_storage(self, name: str) -> CommonStorage:
        return UnQLiteStorage(self.database, name)

    @property
    def user_records(self) -> UserRecordStorage:
        return UserRecordStorage(self.get_common_storage("users"))

    @property
    def profile_records(self) -> ProfileRecordStorage:
        return ProfileRecordStorage(self.get_common_storage("profiles"))

    @property
    def mailbox_records(self) -> MailBoxRecordStorage:
        return MailBoxRecordStorage(self.get_common_storage("mailboxs"))

    @property
    def mail_records(self) -> MailRecordStorage:
        return MailRecordStorage(self.get_common_storage("mail_records"))

    @property
    def mailstore(self) -> MailStore:
        return MailStore(self.get_common_storage("mails"))

    @property
    def token_records(self) -> TokenRecordStorage:
        return TokenRecordStorage(self.get_common_storage("tokens"))

    async def get_mailbox(self, boxid: str) -> Optional[MailBox]:
        if not boxid:
            return None
        record = await self.mailbox_records.find_one({"identity": boxid})
        if not record:
            return None
        return MailBox(record, self.mail_records, self.mailstore, self.mailbox_records)

    async def create_user(self, username: str, password: bytes) -> UserRecord:
        profile = await self.profile_records.create_new_profile()
        user = await self.user_records.create_new_user(
            username, password, profile.identity
        )
        for name in MAILBOX_DEFAULT_SETTING:
            mailbox = await self.mailbox_records.create_mailbox()
            user.mailboxes[name] = mailbox.identity
        await self.user_records.update_one({"profileid": user.profileid}, user)
        return user
