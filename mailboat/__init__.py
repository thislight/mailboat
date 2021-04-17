from dataclasses import dataclass
from .usrsys.maildir import MailDirectory
from .mailstore import MailStore
from .usrsys.storage import ProfileRecordStorage, UserRecordStorage
from unqlite import UnQLite
from .utils.storage import CommonStorage, UnQLiteStorage


class StorageHub(object):
    """All storages about mailboat
    """
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
    def mailstore(self) -> MailStore:
        return MailStore(self.get_common_storage("mails"))

    def get_mail_directory(self, boxid: str) -> MailDirectory:
        return MailDirectory(
            self.get_common_storage("mailbox.{}".format(boxid)), self.mailstore
        )


@dataclass
class MailboatContext(object):
    database: UnQLite
    storagehub: StorageHub
