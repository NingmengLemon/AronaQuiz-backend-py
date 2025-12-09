import logging
from datetime import timedelta
from uuid import UUID, uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.session import (
    ACCESS_TOKEN_LIFETIME,
    LoginSession,
    LoginSessionStatus,
)
from app.models.db.user import DBUser
from app.utils.db import in_readonly_transaction, in_transaction
from app.utils.misc import utcnow
from app.utils.security import sha256, verify

logger = logging.getLogger("uvicorn.error")


@in_transaction()
async def login(
    session: AsyncSession,
    *,
    password: str,
    username: str | None = None,
    user_id: UUID | None = None,
    email: str | None = None,
) -> tuple[UUID, UUID] | None:
    if user_id is not None:
        cond = DBUser.id == user_id
    elif username is not None:
        cond = DBUser.username == username
    elif email is not None:
        cond = DBUser.email == email
    else:
        raise ValueError("missing user identifier")

    user = (await session.exec(select(DBUser).where(cond))).one_or_none()
    if user is None:
        return None
    if not await verify(user.password_hash, password):
        return None
    refresh_token = uuid4()
    new_session = LoginSession(
        user_id=user.id,
        refresh_token_hash=await sha256(refresh_token),
    )
    session.add(new_session)
    await session.flush()
    # await session.commit()
    return new_session.access_token, refresh_token


@in_readonly_transaction()
async def query_login_session(
    session: AsyncSession,
    *,
    access_token: UUID | None = None,
    session_id: UUID | None = None,
) -> LoginSession | None:
    if access_token is not None:
        cond = LoginSession.access_token == access_token
    elif session_id is not None:
        cond = LoginSession.id == session_id
    else:
        raise ValueError("missing login session identifier")
    return (await session.exec(select(LoginSession).where(cond))).one_or_none()


@in_transaction()
async def validate_login_session(
    session: AsyncSession, access_token: UUID
) -> tuple[LoginSessionStatus, LoginSession | None]:
    login_session = await query_login_session(session, access_token=access_token)
    if login_session is None:
        return LoginSessionStatus.INVALID, None

    if login_session.status == LoginSessionStatus.EXPIRED:
        return LoginSessionStatus.EXPIRED, None
    now = utcnow()
    if login_session.expires_at <= now:
        if login_session.status == LoginSessionStatus.ACTIVE:
            login_session.status = LoginSessionStatus.EXPIRED
            session.add(login_session)
            await session.flush()
            # await session.commit()
        return LoginSessionStatus.EXPIRED, None

    if login_session.status == LoginSessionStatus.ACTIVE:
        login_session.last_active = now
        session.add(login_session)
        await session.flush()
        # await session.commit()
        return LoginSessionStatus.ACTIVE, login_session

    return LoginSessionStatus.INVALID, None


@in_transaction()
async def refresh_access_token(
    session: AsyncSession, access_token: UUID, refresh_token: UUID
) -> tuple[UUID, UUID | None] | None:
    login_session = (
        await session.exec(
            select(LoginSession).where(LoginSession.access_token == access_token)
        )
    ).one_or_none()
    if login_session is None:
        return None
    if not (login_session.refresh_token_hash == await sha256(refresh_token)):
        return None

    new_access_token = login_session.access_token = uuid4()
    login_session.last_renewal = utcnow()
    login_session.expires_at = login_session.last_renewal + timedelta(
        days=ACCESS_TOKEN_LIFETIME
    )
    session.add(login_session)
    await session.flush()
    # await session.commit()
    return new_access_token, None


@in_transaction()
async def logout(session: AsyncSession, access_token: UUID) -> bool:
    login_session = (
        await session.exec(
            select(LoginSession).where(LoginSession.access_token == access_token)
        )
    ).one_or_none()
    if login_session is None:
        return False
    login_session.status = LoginSessionStatus.REVOKED
    session.add(login_session)
    await session.flush()
    # await session.commit()
    return True
