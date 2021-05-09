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

import asyncio
import logging
from email.message import EmailMessage

import aiosmtplib
import pytest
from mailboat.mta import TransferAgent, smtpd_auth_rejectall
from unqlite import UnQLite


class TestTransferAgent:
    @pytest.mark.asyncio
    async def test_local_delivery_in_unqlite_memory_queue(self, unused_tcp_port: int):
        virtual_box = []
        database = UnQLite(":mem:")

        async def delivery_handler(email: EmailMessage):
            virtual_box.append(email)

        ta = TransferAgent(
            mydomains=["localhost"],
            hostname="localhost",
            database=database,
            local_delivery_handler=delivery_handler,
            smtpd_auth_handler=smtpd_auth_rejectall,
            smtpd_port=unused_tcp_port,
        )

        try:
            ta.start()
            email = EmailMessage()
            email["Message-Id"] = "<test1@localhost>"
            email["To"] = "user@localhost"
            email["From"] = "qa@localhost"
            await aiosmtplib.send(email, hostname="localhost", port=unused_tcp_port)

            async def wait_virtual_box():
                while len(virtual_box) < 1:
                    await asyncio.sleep(0)

            await asyncio.wait_for(wait_virtual_box(), 1)
            assert isinstance(virtual_box[0], EmailMessage)
            message = virtual_box[0]
            assert message["message-id"] == "<test1@localhost>"
            assert message["to"] == "user@localhost"
            assert message["from"] == "qa@localhost"
        finally:
            ta.destory()
