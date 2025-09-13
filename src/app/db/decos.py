import functools
from collections.abc import Awaitable, Callable
from typing import Concatenate, Protocol

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.utils import auto_begin
from app.typ import AsyncCallable, P, T, T_co


def in_session(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[Concatenate[AsyncSession, P], T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        async with session:
            result = await func(session, *args, **kwargs)
        return result

    return wrapped


def catch_db_exceptions(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[Concatenate[AsyncSession, P], T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(session, *args, **kwargs)
        except Exception as e:
            raise HTTPException(500) from e

    return wrapped


class DatabaseAsyncCallable(Protocol[P, T_co]):
    def __call__(
        self, session: AsyncSession, *args: P.args, **kwargs: P.kwargs
    ) -> Awaitable[T_co]: ...


def in_transaction(
    auto_rollback: bool = True,
) -> Callable[[DatabaseAsyncCallable[P, T]], DatabaseAsyncCallable[P, T]]:
    def deco(func: DatabaseAsyncCallable[P, T]) -> DatabaseAsyncCallable[P, T]:
        @functools.wraps(func)
        async def wrapped(
            session: AsyncSession, *args: P.args, **kwargs: P.kwargs
        ) -> T:
            async with auto_begin(session, auto_rollback=auto_rollback):
                return await func(session, *args, **kwargs)

        return wrapped

    return deco
