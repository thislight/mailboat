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
from typing import AsyncIterator, Optional, Tuple
from .usr import MailRecord
from ..mailstore import MailStore, MailStoreRecord
from ..utils.storage import CommonStorage
from .storage import MailDirectoryStorage


class MailDirectory(object):
    def __init__(self, common_storage: CommonStorage, mailstore: MailStore) -> None:
        self.mail_directory_store = MailDirectoryStorage(common_storage)
        self.mailstore = mailstore
        super().__init__()

    async def store_mail(self, path: str, mail: EmailMessage, exists_ok: bool = False):
        if not exists_ok:
            if await self.exists_mail(mail["message-id"]):
                raise KeyError
        mail_store_record = await self.mailstore.store_mail(mail)
        mail_record = MailRecord(path=path, message_id=mail_store_record.message_id)
        await self.mail_directory_store.store(mail_record)

    async def get_mails(
        self, path_prefix: str
    ) -> AsyncIterator[Tuple[MailRecord, Optional[MailStoreRecord]]]:
        async for doc in self.mail_directory_store.find({}):
            if doc.path.startswith(path_prefix):
                yield (
                    doc,
                    (await self.mailstore.find_one({"message_id": doc.message_id}))
                    if doc.message_id
                    else None,
                )

    async def exists_mail(self, message_id: str) -> bool:
        record = await self.mail_directory_store.find_one({"message_id": message_id})
        return not not record
