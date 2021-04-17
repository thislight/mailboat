from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class UserRecord(object):
    nickname: str
    username: str
    password_b64hash: str
    profileid: str
    mailbox_id: str
    email_address: Optional[str] = None


@dataclass
class ProfileRecord(object):
    identity: str  # should be a UUID string
    member_no: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    physical_sex: Optional[Literal["male", "female"]] = None


@dataclass
class MailRecord(object):
    path: str
    message_id: Optional[str]
