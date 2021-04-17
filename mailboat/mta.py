import asyncio
import email.policy
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from email.headerregistry import BaseHeader
from email.message import EmailMessage
from email.parser import Parser
import logging
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple, cast
import aiosmtplib
import aiosmtpd

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from aiosmtpd.smtp import AuthResult, Envelope, LoginPassword, SMTP, Session
from aiosmtplib.errors import SMTPAuthenticationError
from flanker.addresslib import address
from unqlite import Collection, UnQLite

from asyncio.locks import Lock

from base64 import standard_b64decode, standard_b64encode

from .utils.perf import async_perf_point

LocalDeliveryHandler = Callable[[EmailMessage], Awaitable[Any]]
SMTPAuthHandler = Callable[[SMTP, str, Any], Awaitable[AuthResult]] # the second parameter is method, the third is the data.
# As method "login", "plain", the data is a `LoginPassword`

class EmailQueue(Protocol):
    def get(self) -> Awaitable[Tuple[EmailMessage, int]]:
        ...

    def remove(self, index: int) -> Awaitable[None]:
        ...

    def put(self, email: EmailMessage) -> Awaitable[None]:
        ...


@dataclass
class DeliveryTask(object):
    message_id: str
    delivering_address: str
    done: bool
    success: bool
    status_message: Optional[str] = None
    tried: int = 0


class _SMTPDHandler(AsyncMessage):  # TODO: support OAuth2
    __logger = logging.getLogger("mailboat.mta._SMTPDHandler")

    def __init__(
        self,
        message_handler: Callable[[EmailMessage], Awaitable[Any]],
        smtp_auth_handler: SMTPAuthHandler,
    ) -> None:
        self.smtp_auth_handler = smtp_auth_handler
        self.message_handler = message_handler
        self.delivery_tasks: List[DeliveryTask] = []
        super().__init__()

    async def auth_LOGIN(self, server: SMTP, args: List[str]) -> AuthResult:
        username = await server.challenge_auth("Username:")
        if username == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        else:
            username = standard_b64decode(cast(bytes, username))
        password = await server.challenge_auth("Password:")
        if password == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        else:
            password = standard_b64decode(cast(bytes, password))
        return await self.smtp_auth_handler(
            server, "login", LoginPassword(cast(bytes, username), cast(bytes, password))
        )

    async def auth_PLAIN(self, server: SMTP, args: List[str]) -> AuthResult:
        words = await server.challenge_auth("", encode_to_b64=False)
        if words == aiosmtpd.smtp.MISSING:
            return AuthResult(success=False, handled=False)
        decoded_words = standard_b64decode(cast(bytes, words))
        parts = decoded_words.split(b"\0")
        if parts:
            if not parts[0]:
                parts.pop(0)
        if len(parts) != 2:
            return AuthResult(success=False, handled=True)
        return await self.smtp_auth_handler(
            server, "plain", LoginPassword(parts[0], parts[1])
        )

    async def handle_message(self, message: EmailMessage):
        await self.message_handler(message)


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
            await asyncio.sleep(0)  # TODO (rubicon): more effective way to block coroutine
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
        self.delivery_tasks: List[DeliveryTask] = []
        self.smtpd_controller = Controller(
            _SMTPDHandler(
                self.handle_message,
                smtp_auth_handler=smtpd_auth_handler,
            ),
            port=smtpd_port,
            hostname=hostname,
        )
        self.local_delivery_handler = local_delivery_handler
        self._task_deliveryman = asyncio.ensure_future(self._cothread_deliveryman())

    def destory(self):  # TODO (rubicon): provide method for graceful shutdown
        self.smtpd_controller.stop()
        self._task_deliveryman.cancel("transfer agent destory")

    def start(self):
        self.smtpd_controller.start()

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
                    delivery_task = DeliveryTask(
                        message["message-id"],
                        delivering_address=delivered_to.address,
                        done=False,
                        success=False,
                    )
                    self.delivery_tasks.append(
                        delivery_task
                    )
                    # TODO (rubicon): use a eventbus instead a list for delivery tasks
                    if delivered_to.hostname in self.mydomains:
                        fut = asyncio.ensure_future(
                            self.local_delivery_handler(message)
                        )

                        @fut.add_done_callback
                        def when_local_delivery_done(fut: Future):
                            asyncio.ensure_future(self.queue.remove(index))
                            delivery_task.done = True
                            if not fut.exception():
                                delivery_task.success = True
                            else:
                                delivery_task.success = False
                                delivery_task.status_message = str(fut.exception())

                    else:
                        fut = asyncio.ensure_future(self.remote_deliver(message))

                        @fut.add_done_callback
                        def when_remote_delivery_done(fut: Future):
                            asyncio.ensure_future(self.queue.remove(index))
                            delivery_task.done = True
                            if not fut.exception():
                                delivery_task.success = True
                            else:
                                delivery_task.success = False
                                delivery_task.status_message = str(fut.exception())

            except Exception as e:
                __logger.exception(exc_info=e)


async def smtpd_auth_rejectall(*args, **kargs):
    return AuthResult(success=False, handled=True)
