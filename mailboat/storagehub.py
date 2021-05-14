"""This module contains `StorageHub`, the storage centre of mailboat.
"""
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
    """The storage centre for mailboat. This class stores storages keep mailboat storing data.

    ..note:: Typically you use the one from `mailboat.Mailboat`.

    Related:

    - `mailboat.utils.storage` The abstract storage layer of mailboat.
    """

    def __init__(self, database: UnQLite) -> None:
        self.database = database
        """The database instance.
        .. important:: Don't depends on this property, mailboat may support more database backend in future."""
        super().__init__()

    def get_common_storage(self, name: str) -> CommonStorage:
        """Get a common storage with `name`."""
        return UnQLiteStorage(self.database, name)

    @property
    def user_records(self) -> UserRecordStorage:
        """
        Related:

        - `mailboat.usrsys.usr.UserRecord` The object being stored.
        """
        return UserRecordStorage(self.get_common_storage("users"))

    @property
    def profile_records(self) -> ProfileRecordStorage:
        """
        Related:

        - `mailboat.usrsys.usr.ProfileRecord` The object being stored.
        """
        return ProfileRecordStorage(self.get_common_storage("profiles"))

    @property
    def mailbox_records(self) -> MailBoxRecordStorage:
        """
        Related:

        - `mailboat.usrsys.usr.MailBoxRecord` The object being stored.
        """
        return MailBoxRecordStorage(self.get_common_storage("mailboxs"))

    @property
    def mail_records(self) -> MailRecordStorage:
        """
        Related:

        - `mailboat.usrsys.usr.MailRecord` The object being stored.
        """
        return MailRecordStorage(self.get_common_storage("mail_records"))

    @property
    def mailstore(self) -> MailStore:
        """
        .. tips:: Don't confuse it to `mail_records` and `mailbox_records`, mail store is for storing mail **itself**.

        Related:

        - `mailboat.mailstore.MailStoreRecord` The object being stored.
        """
        return MailStore(self.get_common_storage("mails"))

    @property
    def token_records(self) -> TokenRecordStorage:
        """
        Related:

        - `mailboat.usrsys.tk.TokenRecord` The object being stored.
        """
        return TokenRecordStorage(self.get_common_storage("tokens"))

    async def get_mailbox(self, boxid: str) -> Optional[MailBox]:
        """Get a logic mailbox with `boxid` as identity.
        Return `None` only when the record of `boxid` not found.
        """
        if not boxid:
            return None
        record = await self.mailbox_records.find_one({"identity": boxid})
        if not record:
            return None
        return MailBox(record, self.mail_records, self.mailstore, self.mailbox_records)

    async def create_user(self, username: str, password: bytes) -> UserRecord:
        """Create a user and set up default mailboxes for it.

        Related:

        - `mailboat.usrsys.usr` For the default mailbox names.
        """
        profile = await self.profile_records.create_new_profile()
        user = await self.user_records.create_new_user(
            username, password, profile.identity
        )
        for name in MAILBOX_DEFAULT_SETTING:
            mailbox = await self.mailbox_records.create_mailbox()
            user.mailboxes[name] = mailbox.identity
        await self.user_records.update_one({"profileid": user.profileid}, user)
        return user
