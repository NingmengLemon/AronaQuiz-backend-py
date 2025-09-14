import asyncio
import functools
from collections.abc import Callable
from typing import Any, cast

from app.typ import AsyncCallable, P, T

_SINGLETON_MAP: dict[Any, Any] = {}


def singleton(cls: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(cls)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        if cls not in _SINGLETON_MAP:
            _SINGLETON_MAP[cls] = cls(*args, **kwargs)
        return cast(T, _SINGLETON_MAP[cls])

    return wrapped


def in_thread(func: Callable[P, T]) -> AsyncCallable[P, T]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper
