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
from typing import Optional
import pytest
import aiosmtplib
from aioimaplib import aioimaplib
from email.message import EmailMessage
from mailboat import Mailboat


def imap_response_find_value_of(data: list[str], key: str) -> Optional[str]:
    r"""IMAP responses have many key-value pairs and most are in value-key representation.
    ````
        3 SELECT "Inbox"
        * FLAGS (\Answered \Flagged \Deleted \Seen \Draft $Forwarded)
        * 6951 EXISTS
        * 0 RECENT
    ````
    This function is for to search though data and get the value of specific key (ignore lettercase).

    For example:
    ````python
    result = imap_response_find_value_of(data, "recent")
    # result is "0"
    result1 = imap_response_find_value_of(data, "not_exists")
    # result1 is None
    ````
    """
    for x in data:
        parts = x.strip().split(" ")
        if len(parts) == 2 and parts[1].lower() == key.lower():
            return parts[0]
    return None


@pytest.fixture
def mailboat():
    instance = Mailboat(
        hostname="localhost",
        mydomains="foo.bar",
        database_path=":mem:",
        auth_require_tls=False,  # TODO: add tests to check if the option enabled by default
    )
    try:
        instance.start()
        yield instance
    finally:
        instance.stop()


class TestMailboatFunction:
    @pytest.mark.asyncio
    async def test_sending_and_receiving_email(self, mailboat):
        # Here we have two friends: Alyx and Freeman
        # Today Alyx wants to try out mailboat, she sign up a account
        await mailboat.new_user("alyx", "Alyx", "alyx@foo.bar", "alyxpassword")
        # She knows that freeman also have a account on that
        await mailboat.new_user(
            "freeman", "Freeman", "freeman@foo.bar", "freemanpassword"
        )
        # Alyx sends a hello mail to freeman
        alyx_hello_mail = EmailMessage()
        alyx_hello_mail["from"] = "alyx@foo.bar"
        alyx_hello_mail["to"] = "freeman@foo.bar"
        alyx_hello_mail["subject"] = "Hello, Freeman! I am using mailboat."
        alyx_hello_mail.set_content(
            "I am writing to you and I am using mailboat's server now."
        )
        alyx_hello_mail.set_charset("UTF8")
        (responses, status) = await aiosmtplib.send(
            alyx_hello_mail,
            hostname="localhost",
            port=mailboat.smtpd_port,
            username="alyx",
            password="alyxpassword",
        )
        assert status == "OK"
        # Freeman sign in to IMAP mailbox
        freeman_imap_client = aioimaplib.IMAP4(port=mailboat.imapd_port)
        await freeman_imap_client.wait_hello_from_server()
        await freeman_imap_client.login("freeman", "freemanpassword")
        result, data = await freeman_imap_client.select("INBOX")
        assert result == "OK"
        assert (
            imap_response_find_value_of(data, "recent") == "1"
        ), "Freeman's inbox should only have one new mail"
        # He search for alyx's email
        result, data = await freeman_imap_client.search("FROM", "alyx@foo.bar")
        assert data[0]
        msg_seq_nums = data[0].split(",")
        assert len(msg_seq_nums) == 1
        the_seq_num = msg_seq_nums[0]
        # He read the mail
        result, data = await freeman_imap_client.fetch(the_seq_num, "BODY.PEEK[]")
        assert result == "OK"
        assert data
        # TODO: check the mail content
        # He mark the mail is seen
        (result,) = await freeman_imap_client.store(
            the_seq_num, "+FLAGS", "(\\Deleted \\Seen)"
        )
        assert result == "OK"
        # Freeman write a reply for alyx
        freeman_reply = EmailMessage()
        freeman_reply["from"] = "freeman@foo.bar"
        freeman_reply["to"] = "alyx@foo.bar"
        # TODO: check reply
        freeman_reply["subject"] = "Wow! Welcome here!"
        freeman_reply.set_content("It's great to see you here.")
        (responses, status) = await aiosmtplib.send(
            freeman_reply,
            hostname="localhost",
            port=mailboat.smtpd_port,
            username="freeman",
            password="freemanpassword",
        )
        assert status == "OK"
        # Freeman leaves
        await freeman_imap_client.logout()
        # Alyx sign in to IMAP mailbox
        alyx_imap_client = aioimaplib.IMAP4(port=mailboat.imapd_port)
        await alyx_imap_client.wait_hello_from_server()
        await alyx_imap_client.login("alyx", "alyxpassword")
        result, data = await alyx_imap_client.select("INBOX")
        assert result == "OK"
        assert (
            imap_response_find_value_of(data, "recent") == "1"
        ), "Alyx's inbox should only have one new mail"
        # She search for freeman's email
        result, data = await alyx_imap_client.search("FROM", "alyx@foo.bar")
        assert data[0]
        msg_seq_nums = data[0].split(",")
        assert len(msg_seq_nums) == 1
        the_seq_num = msg_seq_nums[0]
        # She read the mail
        result, data = await alyx_imap_client.fetch(the_seq_num, "BODY.PEEK[]")
        assert result == "OK"
        assert data
        # TODO: check the mail content
        # She mark the mail is seen
        (result,) = await alyx_imap_client.store(
            the_seq_num, "+FLAGS", "(\\Deleted \\Seen)"
        )
        assert result == "OK"
        # Alyx leaves
        await alyx_imap_client.logout()
