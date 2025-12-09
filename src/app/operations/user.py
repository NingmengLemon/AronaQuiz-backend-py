from typing import overload
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.user import DBUser, UserRole
from app.utils.db import in_transaction
from app.utils.security import hash


@overload
async def query_user(session: AsyncSession, *, username: str) -> DBUser | None: ...


@overload
async def query_user(session: AsyncSession, *, user_id: UUID) -> DBUser | None: ...


async def query_user(
    session: AsyncSession,
    *,
    username: str | None = None,
    user_id: UUID | None = None,
) -> DBUser | None:
    if not ((username is None) ^ (user_id is None)):
        raise ValueError("choose from username and user_id")
    return (
        await session.exec(
            select(DBUser).where(
                DBUser.username == username if username else DBUser.id == user_id
            )
        )
    ).one_or_none()


@in_transaction()
async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    nickname: str,
    role: UserRole = UserRole.USER,
) -> UUID:
    hashed_passwd = await hash(password)
    user = DBUser(
        email=email,
        username=username,
        password_hash=hashed_passwd,
        nickname=nickname,
        role=role,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    # await session.commit()
    return user.id
