"""This module contains definitions about users, profiles and mailboxes.
"""
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Set


MAILBOX_INBOX = "Inbox"
MAILBOX_DRAFTS = "Drafts"
MAILBOX_SENT = "Sent"
MAILBOX_ARCHIVES = "Archives"
MAILBOX_JUNK = "Junk"
MAILBOX_DELETED = "Deleted"

MAILBOX_DEFAULT_SETTING = [
    MAILBOX_INBOX,
    MAILBOX_DRAFTS,
    MAILBOX_SENT,
    MAILBOX_ARCHIVES,
    MAILBOX_JUNK,
    MAILBOX_DELETED,
]
"""The default mailboxes for users: Inbox, Drafts, Sent, Archives, Junk, Deleted.
"""


@dataclass
class UserRecord(object):
    """Infomation about user.

    Attributes:
        nickname: `str`. The public name, which shown as name but not unique.
        username: `str`. Unique identity choose by user.
        password_b64hash: `str`. Hashed password. See `mailboat.utils.asec.password_hashing`.
        profileid: `str`. Profile identity.
        mailboxes: `Dict[str, str]`. Mailboxes own by user, the key is the name, the value is the mailbox identity.
        email_address: `Optional[str]`. The user's email address.
    """

    nickname: str
    username: str
    password_b64hash: str
    profileid: str
    mailboxes: Dict[str, str]  # name, mailbox id
    email_address: Optional[str] = None


@dataclass
class ProfileRecord(object):
    """Infomation about people.

    Attributes:
        identity: A UUID `str`, which refered as profile identity.
        member_no: `Optional[str]`. Any number as a member of anything.
        name: `Optional[str]`. The name which only is shown to granted people.
        age: `Optional[int]`. Any number about age.
        physical_sex: `Optional[Literal["male", "female"]]`. As named.

    ..TODO:: add a field about social sex or self-identified sex?
    """

    identity: str  # should be a UUID string
    member_no: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    physical_sex: Optional[Literal["male", "female"]] = None


@dataclass
class MailBoxRecord(object):
    """MailBoxRecord saves meta infomation about one mailbox.

    Attributes:
        identity: A `str` of mailbox identity.
        readonly: A `bool` about if the mailbox is readonly.
        permanent_flags: A `Set[str]` about permanent_flags on the mailbox.

    ..TODO:: remove `session_flags`, which is the flags only avaliable during a (IMAP) session.
    """

    identity: str
    readonly: bool
    permanent_flags: Set[str]
    session_flags: Set[str]


@dataclass
class MailRecord(object):
    """MailRecord is a mark about one mailbox's ownership of an email message.

    Attributes:
        mailbox_id: A `str` of the owner mailbox id.
        message_id: A `str` of the message-id of the email message.
    """

    mailbox_id: str
    message_id: str
