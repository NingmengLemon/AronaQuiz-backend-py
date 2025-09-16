import hashlib
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY

from .decos import in_thread

hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


@in_thread
def hash(password: str | bytes) -> str:
    return hasher.hash(password)


@in_thread
def verify(hashed: str | bytes, password: str | bytes) -> bool:
    try:
        hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False
    return True


@in_thread
def sha256(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
