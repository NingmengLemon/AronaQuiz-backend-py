from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated, Any, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from limits import RateLimitItem
from limits import parse as parse_limit
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import RateLimiter, SlidingWindowCounterRateLimiter
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import DBUser, LoginSession, LoginSessionStatus, UserRole
from app.utils.speedlimit import get_ipaddr, get_remote_address

_SessionGetterType = Callable[[], AsyncSession]
_session_getter: _SessionGetterType | None = None
_speedlimiter: RateLimiter = SlidingWindowCounterRateLimiter(MemoryStorage())
_speedlimit_descriptor: RateLimitItem = parse_limit("6/minute")


def set_session_getter(getter: _SessionGetterType | None) -> None:
    global _session_getter
    _session_getter = getter


class NotReadyError(Exception):
    """session getter not setup yet"""


async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_getter is None:
        raise NotReadyError()
    async with _session_getter() as session:
        yield session


DbSessionDep = Annotated[AsyncSession, Depends(_get_session)]


def config_speedlimiter(
    limiter: RateLimiter | None = None, descriptor: RateLimitItem | str | None = None
) -> tuple[RateLimiter, RateLimitItem]:
    global _speedlimiter
    global _speedlimit_descriptor
    if limiter is not None:
        _speedlimiter = limiter
    if isinstance(descriptor, str):
        _speedlimit_descriptor = parse_limit(descriptor)
    elif isinstance(descriptor, RateLimitItem):
        _speedlimit_descriptor = descriptor
    return _speedlimiter, _speedlimit_descriptor


async def _speedlimit_entrance(request: Request) -> Request:
    if await _speedlimiter.hit(
        _speedlimit_descriptor,
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

    loginsession = (
        await session.exec(
            select(LoginSession).where(LoginSession.access_token == token)
        )
    ).one_or_none()
    if loginsession is None:
        raise HTTPException(401, "会话无效")

    if (
        loginsession.expires_at >= datetime.now()
        and loginsession.status == LoginSessionStatus.ACTIVE
    ):
        loginsession.status = LoginSessionStatus.EXPIRED
        session.add(loginsession)
        raise HTTPException(401, "凭据过期")
    if loginsession.status == LoginSessionStatus.EXPIRED:
        raise HTTPException(401, "凭据过期")

    if loginsession.status == LoginSessionStatus.ACTIVE:
        loginsession.last_active = datetime.now()
        session.add(loginsession)
        return loginsession

    raise HTTPException(401, "会话无效")


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

    return Depends(check_role, use_cache=False)
