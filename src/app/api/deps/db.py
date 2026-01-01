from collections.abc import AsyncGenerator, Callable
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

# global vars for injection
session_getter: Callable[[], AsyncSession] | None = None


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    if session_getter is None:
        raise RuntimeError("inject session_getter first")
    async with session_getter() as session:
        # async with session.begin():
        yield session
        await session.commit()


DbSessionDep = Annotated[AsyncSession, Depends(get_session_dependency)]
