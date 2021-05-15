"""Security tools, including password hashing.

Related:

- [nacl.pwhash - PyNaCL documentation](https://pynacl.readthedocs.io/en/latest/api/pwhash/)
- [Password hashing - libsodium documentation](https://doc.libsodium.org/password_hashing)
"""
from . import global_executor
from asyncio import Future, ensure_future, get_running_loop
from nacl.pwhash import argon2id
from base64 import standard_b64decode, standard_b64encode


def password_hashing_sync(password: bytes) -> str:
    """Hash `password`.
    We define the passwords is hashed by argon2id algorithm with SENSITIVE operation and memory limit.
    Then the hashed password will be encoded in base64. The result is an ASCII string.

    ..caution:: This function is synchrounous.
        It may unexecptly block the thread.
    """
    return standard_b64encode(
        argon2id.str(
            password,
            opslimit=argon2id.OPSLIMIT_SENSITIVE,
            memlimit=argon2id.MEMLIMIT_SENSITIVE,
        )
    ).decode("ascii")


def password_check_sync(password: bytes, password_hash: str) -> bool:
    """Check if the `password_hash` matchs `password`.

    ..caution:: This function is synchrounous.
        It may unexecptly block the thread.
    """
    return argon2id.verify(standard_b64decode(password_hash.encode("ascii")), password)


def password_hashing(password: bytes) -> Future[str]:
    """Hash `password` in another thread.

    ..note:: A thread pool executor wrapper for `password_hashing_sync`.
    """
    return ensure_future(
        get_running_loop().run_in_executor(
            global_executor.get(), password_hashing_sync, password
        )
    )


def password_check(password: bytes, password_hash: str) -> Future[bool]:
    """Check if the `password_hash` matchs `password`, in another thread.

    ..note:: A thread pool executor wrapper for `password_checking_sync`.
    """
    return ensure_future(
        get_running_loop().run_in_executor(
            global_executor.get(), password_check_sync, password, password_hash
        )
    )
