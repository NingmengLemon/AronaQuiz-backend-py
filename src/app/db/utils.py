import functools
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, Concatenate

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction
from sqlalchemy.orm import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.typ import AsyncCallable, P, T


@asynccontextmanager
async def auto_begin(
    session: AsyncSession, auto_rollback: bool = True
) -> AsyncGenerator[AsyncSessionTransaction, None]:
    nested = session.in_transaction()

    async with (session.begin_nested if nested else session.begin)() as t:
        try:
            yield t
        except Exception:
            if auto_rollback:
                await session.rollback()
            raise


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
