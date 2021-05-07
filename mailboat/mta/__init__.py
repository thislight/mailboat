import asyncio
import email.policy
import logging
from asyncio import Future
from asyncio.locks import Lock
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from email.headerregistry import BaseHeader
from email.message import EmailMessage
from email.parser import Parser
from typing import Dict, List, Optional, Tuple, cast

import aiosmtplib
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult
from aiosmtplib.errors import SMTPAuthenticationError
from flanker.addresslib import address
from unqlite import Collection, UnQLite

from ..utils.perf import async_perf_point
from .protocols import EmailQueue, LocalDeliveryHandler, SMTPAuthHandler
from .smtp import SMTPDHandler


class UnQLiteEmailMessageQueue(EmailQueue):
    def __init__(self, coll: Collection) -> None:
        self._coll = coll
        self._coll.create()
        self._ids = []
        for doc in self._coll:
            self._ids.append(doc["__id"])
        self.parser = Parser(EmailMessage, policy=email.policy.default)
        self._thread_pool_executor = ThreadPoolExecutor(
            thread_name_prefix="mailboat.mta.unqlite_email_message_queue_executor"
        )
        super().__init__()

    async def get(self) -> Tuple[EmailMessage, int]:
        while len(self._ids) == 0:
            await asyncio.sleep(
                0
            )  # TODO (rubicon): more effective way to block coroutine
        result = self._coll.fetch(self._ids.pop(0))
        doc_id: int = result["__id"]
        message: str = result["message"]
        return cast(EmailMessage, self.parser.parsestr(message)), doc_id

    async def remove(self, index: int) -> None:
        self._coll.delete(index)

    async def put(self, email: EmailMessage) -> None:
        new_id = self._coll.store({"message": email.as_string()})
        self._ids.append(new_id)


class MemoryEmailQueue(EmailQueue):
    def __init__(self) -> None:
        self.container: Dict[int, EmailMessage] = {}
        self.next_read_id = 0
        self.next_set_id = 0
        self.lock_getting = Lock()
        super().__init__()

    async def get(self) -> Tuple[EmailMessage, int]:
        async with self.lock_getting:
            while self.next_read_id >= self.next_set_id:
                await asyncio.sleep(0)
            result = self.container.get(self.next_read_id)
            result_id = self.next_read_id
            self.next_read_id += 1
            if result:
                return result, result_id
            else:
                return await self.get()

    async def remove(self, id: int) -> None:
        assert id in self.container
        del self.container[id]

    async def put(self, message: EmailMessage) -> None:
        self.container[self.next_set_id] = message
        self.next_set_id += 1


class TransferAgent(object):
    # TODO (rubicon): TLS support
    __logger = logging.getLogger("mailboat.mta.TransferAgent")

    def __init__(
        self,
        *,
        mydomains: List[str],
        local_delivery_handler: LocalDeliveryHandler,
        database: UnQLite,
        smtpd_auth_handler: SMTPAuthHandler,
        hostname: str,
        self_name: str = "mailboat.transfer_agent",
        smtpd_port: int = 8025,
        custom_queue: Optional[EmailQueue] = None,
        auth_require_tls: bool = True,
    ) -> None:
        self.mydomains = mydomains
        self.database = database
        self.name = self_name
        self.hostname = hostname
        self.queue = (
            custom_queue
            if custom_queue
            else UnQLiteEmailMessageQueue(
                database.collection("{}.queue".format(self_name))
            )
        )
        self.smtpd_controller = Controller(
            SMTPDHandler(
                self.handle_message,
                smtp_auth_handler=smtpd_auth_handler,
            ),
            port=smtpd_port,
            hostname=hostname,
            auth_require_tls=auth_require_tls,
        )
        self._auth_require_tls = auth_require_tls
        self.local_delivery_handler = local_delivery_handler
        self._task_deliveryman = asyncio.ensure_future(self._cothread_deliveryman())

    def destory(self):  # TODO (rubicon): provide method for graceful shutdown
        self.smtpd_controller.stop()
        self._task_deliveryman.cancel("transfer agent destory")

    def start(self):
        self.smtpd_controller.start()

    @property
    def smtpd_port(self):
        return self.smtpd_controller.port

    @property
    def auth_require_tls(self) -> bool:
        return self._auth_require_tls

    @async_perf_point("TransferAgent.handle_message")
    async def handle_message(self, message: EmailMessage, internal: bool = False):
        if "message-id" not in message:
            return
        mail_to: BaseHeader = message["To"]
        mail_cc: BaseHeader = message["Cc"]
        mail_bcc: BaseHeader = message["BCC"]
        target_address_lists: List[address.AddressList] = []
        for delivering_list in filter(lambda x: x, (mail_to, mail_cc, mail_bcc)):
            target_address_lists.append(
                address.parse_list(delivering_list, strict=True)
            )
        should_be_delivered_to: List[str] = []
        for list in target_address_lists:
            for addr in list:
                if addr.addr_type == "email":
                    if addr.hostname in self.mydomains:
                        should_be_delivered_to.append(
                            addr.address
                        )  # TODO (rubicon): verify spf and dkim before local delivery
                    elif (
                        isinstance(message["X-Peer"], str)
                        and (
                            message["X-Peer"].startswith("127.0.0.1")
                            or message["X-Peer"].startswith("::1")
                            or message["X-Peer"].startswith("localhost")
                        )
                        or internal
                    ):
                        should_be_delivered_to.append(addr.address)
        queue_futures: List[Future] = []
        for addr in should_be_delivered_to:
            msg_copy = deepcopy(message)
            if "delivered-to" in msg_copy:
                del msg_copy["delivered-to"]
            msg_copy["delivered-to"] = addr
            queue_futures.append(asyncio.ensure_future(self.queue.put(msg_copy)))
        await asyncio.gather(*queue_futures)
        self.__logger.info(
            "handled message: {msg_id}".format(msg_id=message["message-id"])
        )

    async def remote_deliver(self, message: EmailMessage):
        for k in ["X-Peer", "X-MailFrom", "X-RcptTo", "Delivered-To"]:
            if k in message:
                del message[k]
        try:
            await aiosmtplib.send(message, use_tls=True)
        except SMTPAuthenticationError:
            pass
        except:
            try:
                await aiosmtplib.send(message, start_tls=True)
            except SMTPAuthenticationError:
                pass
            except:
                await aiosmtplib.send(message)

    async def _cothread_deliveryman(self):  # TODO (rubicon): custom "pipeline"
        __logger = self.__logger.getChild("deliveryman")
        while True:
            try:
                message, index = await self.queue.get()
                if "delivered-to" in message:
                    if "bcc" in message:
                        del message["bcc"]
                        message["bcc"] = message["delivered-to"]
                    delivered_to = address.parse(message["delivered-to"])
                    # TODO (rubicon): use a eventbus instead a list for delivery tasks
                    if delivered_to.hostname in self.mydomains:
                        asyncio.ensure_future(self.local_delivery_handler(message))
                    else:
                        asyncio.ensure_future(self.remote_deliver(message))

            except Exception as e:
                __logger.exception(exc_info=e)


async def smtpd_auth_rejectall(*args, **kargs):
    return AuthResult(success=False, handled=True)
