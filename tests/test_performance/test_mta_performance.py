from email.message import EmailMessage
import logging
from time import perf_counter
from typing import List

import aiosmtplib

from mailboat.mta import MemoryEmailQueue, TransferAgent, smtpd_auth_rejectall
from unqlite import UnQLite

import pytest
import asyncio

from os import environ


@pytest.mark.skipif(
    environ.get("TEST_PERFORMANCE") != "1",
    reason="performance testing will be skipped without TEST_PERFORMANCE=1",
)
class TestTransferAgentPerformance:
    @pytest.mark.asyncio
    async def test_local_delivery_in_unqlite_memory_queue(self, unused_tcp_port: int):
        TEST_MAIL_NUMBER = 100
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
            t1 = perf_counter()
            lost_mail_count = 0
            for x in range(0, TEST_MAIL_NUMBER):
                try:
                    await aiosmtplib.send(
                        email, hostname="localhost", port=unused_tcp_port
                    )
                except:
                    lost_mail_count += 1

            async def wait_virtual_box():
                while len(virtual_box) < TEST_MAIL_NUMBER:
                    await asyncio.sleep(0)

            await asyncio.wait_for(wait_virtual_box(), 12)
            t2 = perf_counter()
            result = t2 - t1
            logging.warning(
                "UnQLiteEmailMessageQueue(:mem:): %f sec./%smails, lost=%d",
                result,
                TEST_MAIL_NUMBER,
                lost_mail_count,
            )
            assert result < (
                TEST_MAIL_NUMBER / 100 * 4
            ), "the MTA performance should be 25 per second at least"
        finally:
            ta.destory()

    @pytest.mark.asyncio
    async def test_performance_local_delivery_in_pure_memory_queue(
        self, unused_tcp_port: int
    ):
        TEST_MAIL_NUMBER = 100
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
            custom_queue=MemoryEmailQueue(),
            smtpd_port=unused_tcp_port,
        )

        try:
            ta.start()
            email = EmailMessage()
            email["Message-Id"] = "<test1@localhost>"
            email["To"] = "user@localhost"
            email["From"] = "qa@localhost"
            t1 = perf_counter()
            lost_mail_count = 0
            for x in range(0, TEST_MAIL_NUMBER):
                try:
                    await aiosmtplib.send(
                        email, hostname="localhost", port=unused_tcp_port
                    )
                except:
                    lost_mail_count += 1

            async def wait_virtual_box():
                while len(virtual_box) < TEST_MAIL_NUMBER:
                    await asyncio.sleep(0)

            await asyncio.wait_for(wait_virtual_box(), 12)
            t2 = perf_counter()
            result = t2 - t1
            logging.warning(
                "MemoryEmailQueue: %f sec./%smails, lost=%d",
                result,
                TEST_MAIL_NUMBER,
                lost_mail_count,
            )
            assert result < (
                TEST_MAIL_NUMBER / 100 * 4
            ), "the MTA performance should be 25 per second at least"
        finally:
            ta.destory()
            if len(virtual_box) != TEST_MAIL_NUMBER:
                pytest.fail(
                    "except {} mails, got {}".format(TEST_MAIL_NUMBER, len(virtual_box))
                )
