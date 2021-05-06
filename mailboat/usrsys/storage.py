from typing import List, Optional
from mailboat.usrsys.tk import TokenRecord
from ..utils.storage import (
    DataclassCommonStorageAdapter,
    CommonStorageRecordWrapper,
    CommonStorage,
)
from .usr import MailBoxRecord, MailRecord, UserRecord, ProfileRecord
from ..utils.asec import password_check


class UserRecordStorage(CommonStorageRecordWrapper[UserRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(UserRecord))

    async def check_user_password(self, username: str, password: bytes) -> bool:
        doc = await self.find_one({"username": username})
        if not doc:
            return False
        return await password_check(password, doc.password_b64hash)

    async def create_new_user(self, username: str, password: bytes) -> bool:
        pass  # TODO (rubicon): create_new_user


class ProfileRecordStorage(CommonStorageRecordWrapper[ProfileRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(ProfileRecord))


class MailBoxRecordStorage(CommonStorageRecordWrapper[MailBoxRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailBoxRecord))


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
