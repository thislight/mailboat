"""This module contains all storage classes for the user system.
"""
from typing import List, Optional
from .tk import TokenRecord
from ..utils.storage import (
    DataclassCommonStorageAdapter,
    CommonStorageRecordWrapper,
    CommonStorage,
)
from .usr import MailBoxRecord, MailRecord, ProfileRecord, UserRecord, ProfileRecord
from ..utils.asec import password_check, password_hashing
from uuid import uuid4


class UserRecordStorage(CommonStorageRecordWrapper[UserRecord]):
    """
    A `mailboat.utils.storage.RecordStorage` for `mailboat.usrsys.usr.UserRecord`.
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(UserRecord))

    async def check_user_password(self, username: str, password: bytes) -> bool:
        """Check the user password.
        ..note:: The `password` is the password in plaintext.
        """
        doc = await self.find_one({"username": username})
        if not doc:
            return False
        return await password_check(password, doc.password_b64hash)

    async def create_new_user(
        self, username: str, password: bytes, profileid: str
    ) -> UserRecord:
        """Create a new user, then save it.
        ..note:: It does not mean the new user is avaliable, you should also create other resources for the user."""
        rec = UserRecord(
            nickname="",
            username=username,
            password_b64hash=await password_hashing(password),
            profileid=profileid,
            mailboxes={},
            email_address=None,
        )
        await self.store(rec)
        return rec


class ProfileRecordStorage(CommonStorageRecordWrapper[ProfileRecord]):
    """
    A `mailboat.utils.storage.RecordStorage` for `mailboat.usrsys.usr.ProfileRecord`.
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(ProfileRecord))

    async def create_new_profile(self) -> ProfileRecord:
        """Create and save a new profile."""
        rec = ProfileRecord(
            identity=uuid4().hex,
        )
        await self.store(rec)
        return rec


class MailBoxRecordStorage(CommonStorageRecordWrapper[MailBoxRecord]):
    """
    A `mailboat.utils.storage.RecordStorage` for `mailboat.usrsys.usr.MailBoxRecord`.
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailBoxRecord))

    async def create_mailbox(self) -> MailBoxRecord:
        """
        Create a new mailbox.
        """
        rec = MailBoxRecord(
            identity=uuid4().hex,
            readonly=False,
            permanent_flags=set(),
            session_flags=set(),
        )
        await self.store(rec)
        return rec


class MailRecordStorage(CommonStorageRecordWrapper[MailRecord]):
    """
    A `mailboat.utils.storage.RecordStorage` for `mailboat.usrsys.usr.MailRecord`.
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailRecord))


class TokenRecordStorage(CommonStorageRecordWrapper[TokenRecord]):
    """
    A `mailboat.utils.storage.RecordStorage` for `mailboat.usrsys.tk.TokenRecord`.
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(TokenRecord))

    async def create_token(
        self,
        profileid: str,
        *,
        appid: Optional[str] = None,
        apprev: Optional[str] = None,
        scope: List[str]
    ):
        """Create a new token."""
        new_record = TokenRecord.new(profileid, appid=appid, apprev=apprev, scope=scope)
        await self.store(new_record)
        return new_record

    async def find_token(self, token: str) -> Optional[TokenRecord]:
        """Find a `mailboat.usrsys.tk.TokenRecord` with `token` as the token string."""
        return await self.find_one({"token": token})
