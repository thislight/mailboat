from asyncio import get_running_loop, Future, ensure_future
from typing import Tuple
import spf
from . import global_executor


def check(
    from_ip: str, from_addr: str, from_domain_name: str
) -> Future[Tuple[str, str]]:
    a = get_running_loop().run_in_executor(
        global_executor.get(), spf.check2, from_ip, from_addr, from_domain_name
    )
    return ensure_future(a)
