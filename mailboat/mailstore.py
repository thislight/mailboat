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
`MailStore` store mails by their message identities.
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
    """A record for storing email.

    Attributes:
        message_id: A `str` of "message-id" from one email.
        raw_email: The `str` from `email.message.EmailMessage.as_string`.
        ref_count: A `int` which maintains for garbage collecting.
    """

    message_id: str
    raw_mail: str
    ref_count: int


class MailStore(CommonStorageRecordWrapper[MailStoreRecord]):
    """Interface for email storing.

    ..note:: This storage identify messages by the header "message-id".
    """

    def __init__(self, common_storage: CommonStorage) -> None:
        super().__init__(common_storage, DataclassCommonStorageAdapter(MailStoreRecord))

    async def store_mail(self, mail: EmailMessage) -> MailStoreRecord:
        """Store a mail with it's message id."""
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
        """Less the mail's reference count by 1.
        If the mail's reference count is not greater than zero, the mail will be deleted.
        Return `None` only when the message not found.

        Args:
            message_id: the message-id of the mail
        """
        record = await self.find_one({"message_id": message_id})
        if record:
            record.ref_count -= 1
            if record.ref_count <= 0:
                await self.remove_one({"message_id": message_id})
            return record
        else:
            return None
