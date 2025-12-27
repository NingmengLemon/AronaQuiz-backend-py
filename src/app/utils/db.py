import functools
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Concatenate, Protocol

from fastapi import HTTPException
from sqlalchemy import URL, Column, Connection, DateTime, Table, inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction
from sqlalchemy.orm import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.typ import AsyncCallable, P, T, T_co


def catch_db_exceptions(
    func: AsyncCallable[Concatenate[AsyncSession, P], T],
) -> AsyncCallable[Concatenate[AsyncSession, P], T]:
    @functools.wraps(func)
    async def wrapped(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(session, *args, **kwargs)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Database operation failed"
            ) from e

    return wrapped


class DatabaseAsyncCallable(Protocol[P, T_co]):
    def __call__(
        self, session: AsyncSession, *args: P.args, **kwargs: P.kwargs
    ) -> Awaitable[T_co]: ...


def in_transaction() -> Callable[
    [DatabaseAsyncCallable[P, T]], DatabaseAsyncCallable[P, T]
]:
    def deco(func: DatabaseAsyncCallable[P, T]) -> DatabaseAsyncCallable[P, T]:
        @functools.wraps(func)
        async def wrapped(
            session: AsyncSession, *args: P.args, **kwargs: P.kwargs
        ) -> T:
            async with auto_begin(session):
                rv = await func(session, *args, **kwargs)
                return rv

        return wrapped

    return deco


def in_readonly_transaction() -> Callable[
    [DatabaseAsyncCallable[P, T]], DatabaseAsyncCallable[P, T]
]:
    """
    只读事务装饰器, 用于查询操作。
    实际上并不能防止意外修改, 但可以作为语义上的区分。
    """

    def deco(func: DatabaseAsyncCallable[P, T]) -> DatabaseAsyncCallable[P, T]:
        @functools.wraps(func)
        async def wrapped(
            session: AsyncSession, *args: P.args, **kwargs: P.kwargs
        ) -> T:
            # 对于只读操作，不需要显式事务，使用现有会话即可
            return await func(session, *args, **kwargs)

        return wrapped

    return deco


@asynccontextmanager
async def auto_begin(
    session: AsyncSession,
) -> AsyncGenerator[AsyncSessionTransaction, None]:
    nested = session.in_transaction()
    async with (session.begin_nested if nested else session.begin)() as t:
        yield t


def to_async(
    maker: Callable[[], AsyncSession],
) -> Callable[[Callable[Concatenate[Session, P], T]], AsyncCallable[P, T]]:
    def deco(func: Callable[Concatenate[Session, P], T]) -> AsyncCallable[P, T]:
        """将执行第一个参数是 Session 的同步函数装饰成异步函数, 运行时会单开一个 AsyncSession"""

        @functools.wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            async with maker() as asess:
                return await asess.run_sync(func, *args, **kwargs)

        return wrapped

    return deco


def get_session(
    engine: AsyncEngine,
    autoflush: bool = False,
    expire_on_commit: bool = False,
    **kwargs: Any,
) -> AsyncSession:
    return AsyncSession(
        engine, autoflush=autoflush, expire_on_commit=expire_on_commit, **kwargs
    )


def new_session_getter(
    engine: AsyncEngine,
    autoflush: bool = False,
    expire_on_commit: bool = False,
    **kwargs: Any,
) -> Callable[[], AsyncSession]:
    return functools.partial(
        get_session,
        engine=engine,
        autoflush=autoflush,
        expire_on_commit=expire_on_commit,
        **kwargs,
    )


def new_engine(url: str | URL, echo: bool = False, **kwargs: Any) -> AsyncEngine:
    return create_async_engine(url, echo=echo, **kwargs)


def check_table_existence_sync(conn: Connection, table: Table) -> bool:
    return inspect(conn).has_table(table_name=table.name, schema=table.schema)


async def check_table_existence(session: AsyncSession, table: Table) -> bool:
    async_conn = await session.connection()
    existence = await async_conn.run_sync(check_table_existence_sync, table=table)
    return existence


def datetime_column_tzaware(onupdate: Any | None = None) -> Column[datetime]:
    return Column(DateTime(timezone=True), nullable=False, onupdate=onupdate)
