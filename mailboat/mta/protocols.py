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
"""All the protocol types for `mailboat.mta`.
"""

from typing import Protocol, Callable, Awaitable, Any, Tuple
from aiosmtpd.smtp import AuthResult, SMTP
from email.message import EmailMessage

LocalDeliveryHandler = Callable[[EmailMessage], Awaitable[Any]]
"""A type for handler which do local delivery process."""


SMTPAuthHandler = Callable[[SMTP, str, Any], Awaitable[AuthResult]]
"""A type for handler which do SMTP server authentication process.
The second parameter is method, the third is the data. As method "login", "plain", the data is a `LoginPassword`
"""


class EmailQueue(Protocol):
    """A protocol type for an email queue which is to store coming emails in mail transfering process.

    It's no order promise to this protocol, but typically the implementation should be in FIFO order.

    Related:

    - `mailboat.mta.TransferAgent`
    """

    def get(self) -> Awaitable[Tuple[EmailMessage, int]]:
        """Get one email from queue.
        The second entity of the result is the index, which can be used to remove the mail from the queue.
        """
        ...

    def remove(self, index: int) -> Awaitable[None]:
        """Remove the email as `index` in the queue."""
        ...

    def put(self, email: EmailMessage) -> Awaitable[None]:
        """Put one `email` into queue."""
        ...
