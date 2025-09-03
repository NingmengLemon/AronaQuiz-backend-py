from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio.session import AsyncSessionTransaction
from sqlmodel.ext.asyncio.session import AsyncSession


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
