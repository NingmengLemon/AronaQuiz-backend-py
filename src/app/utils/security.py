from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY

from .decos import in_thread

hasher = PasswordHasher.from_parameters(RFC_9106_LOW_MEMORY)


@in_thread
def hash(passwd: str | bytes) -> str:
    return hasher.hash(passwd)


@in_thread
def verify(hashed: str | bytes, passwd: str | bytes) -> bool:
    try:
        hasher.verify(hashed, passwd)
    except VerifyMismatchError:
        return False
    return True
