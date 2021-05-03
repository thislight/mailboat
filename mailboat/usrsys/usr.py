from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Set

MailboxID = str


@dataclass
class UserRecord(object):
    nickname: str
    username: str
    password_b64hash: str
    profileid: str
    mailboxes: Dict[str, MailboxID]  # name, mailbox id
    email_address: Optional[str] = None


@dataclass
class ProfileRecord(object):
    identity: str  # should be a UUID string
    member_no: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    physical_sex: Optional[Literal["male", "female"]] = None


@dataclass
class MailBoxRecord(object):
    "MailBoxRecord saves meta infomation about one mailbox."
    identity: str
    readonly: bool
    permanent_flags: Set[str]
    session_flags: Set[str]


@dataclass
class MailRecord(object):
    "MailRecord is a mark about one's having one email message."
    mailbox_id: str
    message_id: str 
