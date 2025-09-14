import functools
from collections.abc import AsyncGenerator
from typing import Annotated, Callable

from fastapi import Depends, Request
from limits import RateLimitItem
from limits import parse as parse_limit
from limits.aio.storage import MemoryStorage, Storage
from limits.aio.strategies import RateLimiter, SlidingWindowCounterRateLimiter
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.utils import auto_begin

_SessionGetter = Callable[[], AsyncSession]
_session_getter: _SessionGetter | None = None
_speedlimiter: RateLimiter = SlidingWindowCounterRateLimiter(MemoryStorage())
_speedlimit_descriptor: RateLimitItem = parse_limit("6/minute")


def set_session_getter(getter: _SessionGetter | None) -> None:
    global _session_getter
    _session_getter = getter


class NotReadyError(Exception):
    """session getter not setup yet"""


async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_getter is None:
        raise NotReadyError()
    async with _session_getter() as session:
        async with auto_begin(session):
            yield session


DbSessionDep = Annotated[AsyncSession, Depends(_get_session, use_cache=False)]


def config_speedlimiter(
    limiter: RateLimiter | None = None, descriptor: RateLimitItem | str | None = None
) -> tuple[RateLimiter, RateLimitItem]:
    global _speedlimiter
    global _speedlimit_descriptor
    if limiter is not None:
        _speedlimiter = limiter
    if isinstance(descriptor, str):
        _speedlimit_descriptor = parse_limit(descriptor)
    elif isinstance(descriptor, RateLimitItem):
        _speedlimit_descriptor = descriptor
    return _speedlimiter, _speedlimit_descriptor


async def _speed_limiter_entrance(request: Request) -> Request:
    return request


SpeedLimReqDep = Annotated[Request, Depends(_speed_limiter_entrance)]
