import asyncio
import functools
from collections.abc import AsyncGenerator
from typing import Callable, Concatenate, ParamSpec, TypeVar

from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.schema import Table
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.typ import AsyncCallable

from .models import TABLES

P = ParamSpec("P")
T = TypeVar("T")


class AsyncDatabaseCore:
    class AsyncDbCoreException(Exception):
        "raised when incorrectly operated"

    class NotStarted(AsyncDbCoreException):
        pass

    class AlreadyStarted(AsyncDbCoreException):
        pass

    def __init__(self, dburl: str, tables: list[Table], *, echo: bool = False):
        self._url = dburl
        self._tables = tables
        self._engine = create_async_engine(
            dburl,
            # connect_args={"check_same_thread": False},
            echo=echo,
        )
        self._startup_event = asyncio.Event()

    @property
    def started(self) -> asyncio.Event:
        return self._startup_event

    async def startup(self) -> None:
        if self.started.is_set():
            raise self.AlreadyStarted()
        async with self._engine.begin() as conn:
            await conn.run_sync(
                SQLModel.metadata.create_all, tables=self._tables, checkfirst=True
            )
        self._startup_event.set()

    def get_session(self, autoflush: bool = False) -> AsyncSession:
        """注意返回值是 AsyncSession 而不是 Session"""
        if not self.started.is_set():
            raise self.NotStarted()
        return AsyncSession(self._engine, autoflush=autoflush)

    async def run_sync(
        self,
        func: Callable[Concatenate[Session, P], T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """单开一个 AsyncSession 来执行第一个参数是 Session 的同步函数"""
        async with self.get_session() as asess:
            return await asess.run_sync(func, *args, **kwargs)  # type: ignore

    def to_async(
        self, func: Callable[Concatenate[Session, P], T]
    ) -> AsyncCallable[P, T]:
        """将执行第一个参数是 Session 的同步函数装饰成异步函数, 运行时会单开一个 AsyncSession"""

        @functools.wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            return await self.run_sync(func, *args, **kwargs)

        return wrapped

    async def get_session_yield(
        self, autoflush: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        async with self.get_session(autoflush) as session:
            yield session


class AppDatabase(AsyncDatabaseCore):
    def __init__(self, dburl: str, *, echo: bool = False):
        super().__init__(dburl, TABLES, echo=echo)
