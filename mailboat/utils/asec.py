from . import global_executor
import asyncio
from nacl.pwhash import argon2id
from base64 import standard_b64decode, standard_b64encode


def password_hashing_sync(password: bytes) -> str:
    return standard_b64encode(
        argon2id.str(
            password,
            opslimit=argon2id.OPSLIMIT_SENSITIVE,
            memlimit=argon2id.MEMLIMIT_SENSITIVE,
        )
    ).decode("ascii")


def password_check_sync(password: bytes, password_hash: str) -> bool:
    return argon2id.verify(standard_b64decode(password_hash.encode("ascii")), password)


def password_hashing(password: bytes) -> asyncio.Future[str]:
    return asyncio.ensure_future(
        asyncio.get_running_loop().run_in_executor(
            global_executor.get(), password_hashing_sync, password
        )
    )


def password_check(password: bytes, password_hash: str) -> asyncio.Future[bool]:
    return asyncio.ensure_future(
        asyncio.get_running_loop().run_in_executor(
            global_executor.get(), password_check_sync, password, password_hash
        )
    )
