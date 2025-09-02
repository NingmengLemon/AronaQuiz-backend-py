import functools
from typing import Concatenate, ParamSpec, TypeVar

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.typ import AsyncCallable

T = TypeVar("T")
P = ParamSpec("P")


def in_session(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[..., T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        async with session:
            result = await func(session, *args, **kwargs)
        return result

    return wrapped


def catch_db_exceptions(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[..., T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(session, *args, **kwargs)
        except Exception as e:
            raise HTTPException(500) from e

    return wrapped


def in_transaction(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[..., T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        async with session.begin():
            return await func(session, *args, **kwargs)

    return wrapped


def in_nested_transaction(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[..., T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        async with session.begin_nested():
            return await func(session, *args, **kwargs)

    return wrapped
