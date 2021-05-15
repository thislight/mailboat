"""This module contains function to check infomation for the Sender Policy Framework.

> Sender Policy Framework (SPF) is an email authentication method designed to detect forging sender addresses during the delivery of the email.
> -- Wikipedia

Related:

- [Sender Policy Framework - Wikipedia](https://en.wikipedia.org/wiki/Sender_Policy_Framework)
- [Open SPF](http://www.open-spf.org)
- [RFC 7208: Sender Policy Framework (SPF) for Authorizing Use of Domains in Email, Version 1](https://datatracker.ietf.org/doc/html/rfc7208)
- [RFC 8616: Email Authentication for Internationalized Mail](https://datatracker.ietf.org/doc/html/rfc8616)
"""
from asyncio import get_running_loop, Future, ensure_future
from typing import Tuple, Literal, Union
import spf
from . import global_executor

SPF_STATUS = Union[
    Literal["pass"],
    Literal["fail"],
    Literal["neutral"],
    Literal["softfail"],
    Literal["permerror"],
    Literal["temperror"],
]


def check(
    from_ip: str, from_addr: str, from_domain_name: str
) -> Future[Tuple[SPF_STATUS, str]]:
    """Verify for `from_ip`, `from_addr`, `from_domain_name`.

    ..note:: This function is just a thread pool executor wrapper for `spf.check2`.

    The first element of result is one of "pass", "fail", "neutral", "softfail", "permerror", or "temperror".
    The second is explaination.

    Related:

    - [pyspf - PyPI](https://pypi.org/project/pyspf/)
    """
    a = get_running_loop().run_in_executor(
        global_executor.get(), spf.check2, from_ip, from_addr, from_domain_name
    )
    return ensure_future(a)
