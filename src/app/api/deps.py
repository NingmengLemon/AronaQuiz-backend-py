from collections.abc import AsyncGenerator
from typing import Annotated, Callable

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

_SessionGetter = Callable[[], AsyncSession]
_session_getter: _SessionGetter | None = None


def set_session_getter(getter: _SessionGetter | None) -> None:
    global _session_getter
    _session_getter = getter


class NotReadyError(Exception):
    """session getter not setup yet"""


async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_getter is None:
        raise NotReadyError()
    async with _session_getter() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(_get_session, use_cache=False)]
