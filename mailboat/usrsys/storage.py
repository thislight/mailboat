from ..utils.storage import (
    DataclassCommonStorageAdapter,
    CommonStorageRecordWrapper,
    CommonStorage,
)
from .usr import MailRecord, UserRecord, ProfileRecord
from ..utils.asec import password_check


class UserRecordStorage(CommonStorageRecordWrapper[UserRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(UserRecord))
    
    async def check_user_password(self, username: str, password: bytes) -> bool:
        doc = await self.find_one({'username': username})
        if not doc:
            return False
        return await password_check(password, doc.password_b64hash)


class ProfileRecordStorage(CommonStorageRecordWrapper[ProfileRecord]):
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(ProfileRecord))


class MailDirectoryStorage(CommonStorageRecordWrapper[MailRecord]):
    def __init__(
        self,
        common_storage: CommonStorage,
    ) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailRecord))
