from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from limits import RateLimitItem
from limits import parse as parse_limit
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import RateLimiter, SlidingWindowCounterRateLimiter
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import DBUser, LoginSession, LoginSessionStatus, UserRole
from app.db.operations import validate_login_session
from app.utils.speedlimit import get_ipaddr, get_remote_address

# global vars for injection
session_getter: Callable[[], AsyncSession] | None = None
speedlimiter: RateLimiter | None = SlidingWindowCounterRateLimiter(MemoryStorage())
speedlimit_descriptor: RateLimitItem = parse_limit("6/minute")


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    if session_getter is None:
        raise RuntimeError("inject session_getter first")
    async with session_getter() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(get_session_dependency)]


async def _speedlimit_entrance(request: Request) -> Request:
    if speedlimiter is None:
        return request

    if await speedlimiter.hit(
        speedlimit_descriptor,
        get_remote_address(request),
        get_ipaddr(request),
    ):
        return request
    else:
        raise HTTPException(429, "请慢一点...!")


SpeedLimReqDep = Depends(_speedlimit_entrance)


async def _check_login(
    session: DbSessionDep, authorization: str = Header("")
) -> LoginSession:
    if len(_ := authorization.split(maxsplit=1)) == 2:
        rawtoken = _[1]
    elif _:
        rawtoken = _[0]
    else:
        raise HTTPException(401, "需要登录")

    try:
        token = UUID(rawtoken)
    except Exception:
        raise HTTPException(400, "凭据非法")

    session_status, login_session = await validate_login_session(
        session, access_token=token
    )
    match session_status:
        case LoginSessionStatus.EXPIRED:
            raise HTTPException(401, "凭据过期")
        case LoginSessionStatus.ACTIVE:
            pass
        case _:
            raise HTTPException(401, "会话无效")
    if login_session is None:
        raise HTTPException(401, "会话无效")

    return login_session


LoginRequired = Annotated[LoginSession, Depends(_check_login)]


def RequireRoles(*roles: UserRole) -> Any:
    async def check_role(
        session: DbSessionDep, login_session: LoginRequired
    ) -> UserRole:
        if (
            role := (
                (
                    await session.exec(
                        select(DBUser).where(DBUser.id == login_session.user_id)
                    )
                )
                .one()
                .role
            )
        ) not in roles:
            raise HTTPException(403, "权限不足")
        return role

    return Depends(check_role)
