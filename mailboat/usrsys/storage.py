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
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(UserRecord))

    async def check_user_password(self, username: str, password: bytes) -> bool:
        doc = await self.find_one({"username": username})
        if not doc:
            return False
        return await password_check(password, doc.password_b64hash)

    async def create_new_user(
        self, username: str, password: bytes, profileid: str
    ) -> UserRecord:
        """Shortcut to create a new user. It does not mean the new user is avaliable, you should also create other resources for the user."""
        rec = UserRecord(
            nickname="",
            username=username,
            password_b64hash=await password_hashing(password),
            profileid=profileid,
            mailboxes={},
            email_address=None,
        )
        self.store(rec)
        return rec


class ProfileRecordStorage(CommonStorageRecordWrapper[ProfileRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(ProfileRecord))

    async def create_new_profile(self) -> ProfileRecord:
        rec = ProfileRecord(
            identity=uuid4().hex,
        )
        self.store(rec)
        return rec


class MailBoxRecordStorage(CommonStorageRecordWrapper[MailBoxRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailBoxRecord))

    async def create_mailbox(self) -> MailBoxRecord:
        rec = MailBoxRecord(
            identity=uuid4().hex,
            readonly=False,
            permanent_flags=set(),
            session_flags=set(),
        )
        self.store(rec)
        return rec


class MailRecordStorage(CommonStorageRecordWrapper[MailRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailRecord))


class TokenRecordStorage(CommonStorageRecordWrapper[TokenRecord]):
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
        new_record = TokenRecord.new(profileid, appid=appid, apprev=apprev, scope=scope)
        await self.store(new_record)
        return new_record

    async def find_token(self, token: str) -> Optional[TokenRecord]:
        return await self.find_one({"token": token})
