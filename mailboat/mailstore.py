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

"""
About mailstore

`MailStore` just care about mails -
it does not know the directory structure, even the user owns it. It just store mails by their message identities.
"""

from email.message import EmailMessage
from dataclasses import dataclass
from typing import Optional
from .utils.storage import (
    CommonStorage,
    DataclassCommonStorageAdapter,
    CommonStorageRecordWrapper,
)


@dataclass
class MailStoreRecord(object):
    message_id: str
    raw_mail: str
    ref_count: int


class MailStore(CommonStorageRecordWrapper[MailStoreRecord]):
    """Interface for emails."""
    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailStoreRecord))

    async def store_mail(self, mail: EmailMessage) -> MailStoreRecord:
        """store a mail with it's message id."""
        assert "message-id" in mail
        msg_id = mail["message-id"]
        record = await self.find_one({"message_id": msg_id})
        if record:
            record.ref_count += 1
            await self.update_one({"message_id": msg_id}, record)
            return record
        else:
            new_record = MailStoreRecord(
                message_id=msg_id,
                raw_mail=mail.as_string(),
                ref_count=1,
            )
            await self.store(new_record)
            return new_record

    async def deref_mail_by_id(self, message_id: str) -> Optional[MailStoreRecord]:
        """Decrease reference count of a mail with `message_id`.
        If the mail's reference count is not greater than zero, it will be deleted.
        """
        record = await self.find_one({"message_id": message_id})
        if record:
            record.ref_count -= 1
            if record.ref_count <= 0:
                await self.remove_one({"message_id": message_id})
            return record
        else:
            return None
