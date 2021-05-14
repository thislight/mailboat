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
`MailBox`: The logic mailbox.
"""
from email.message import EmailMessage
from typing import AsyncIterator, Optional, Tuple
from .usr import MailBoxRecord
from ..mailstore import MailStore, MailStoreRecord
from ..utils.storage import CommonStorage
from .storage import MailBoxRecordStorage, MailRecordStorage


class MailBox(object):
    """Logic mailbox.

    This class is an easy interface to a mailbox.

    Related:

    - `mailboat.usrsys.usr.MailBoxRecord`
    - `mailboat.usrsys.storage.MailRecordStorage`
    - `mailboat.mailstore.MailStore`
    - `mailboat.usrsys.storage.MailBoxRecordStorage`
    """

    def __init__(
        self,
        mailbox_rec: MailBoxRecord,
        mail_rec_storage: MailRecordStorage,
        mail_store: MailStore,
        mailbox_rec_storage: MailBoxRecordStorage,
    ) -> None:
        self.mailbox_record = mailbox_rec
        self.mail_record_storage = mail_rec_storage
        self.mail_store = mail_store
        self.mailbox_record_storage = mailbox_rec_storage
        super().__init__()

    @property
    def id(self):
        """The mailbox identity."""
        return self.mailbox_record.identity

    @property
    def readonly(self):
        return False  # TODO: implement readonly mailbox
