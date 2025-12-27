from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from limits import RateLimitItem
from limits import parse as parse_limit
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import RateLimiter, SlidingWindowCounterRateLimiter
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.exceptions import (
    APIException,
    ForbiddenException,
    UnauthorizedException,
)
from app.models.db.auth import (
    LoginSession,
    LoginSessionStatus,
)
from app.models.db.user import (
    DBUser,
    UserRole,
)
from app.models.dto.code import BusinessCode
from app.repos.auth import AuthRepository
from app.repos.problem import ProblemRepository, ProblemSetRepository
from app.repos.user import UserRepository
from app.repos.tag import TagRepository
from app.services.auth import AuthService
from app.services.problem import ProblemService
from app.services.user import UserService
from app.utils.speedlimit import get_ipaddr, get_remote_address

# global vars for injection
session_getter: Callable[[], AsyncSession] | None = None
speedlimiter: RateLimiter | None = SlidingWindowCounterRateLimiter(MemoryStorage())
speedlimit_descriptor: RateLimitItem = parse_limit("6/minute")


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    if session_getter is None:
        raise RuntimeError("inject session_getter first")
    async with session_getter() as session:
        # async with session.begin():
        yield session
        await session.commit()


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
        raise APIException(
            status_code=429,
            code=BusinessCode.TOO_MANY_REQUESTS,
            message="请慢一点...!"
        )


SpeedLimReqDep = Depends(_speedlimit_entrance)


def get_auth_service(session: DbSessionDep) -> AuthService:
    """获取认证服务实例"""
    return AuthService(
        session=session,
        auth_repo=AuthRepository(),
        user_repo=UserRepository(),
    )


AuthServiceDep = Annotated[
    AuthService,
    Depends(get_auth_service),
]


async def _check_login(
    session: DbSessionDep,
    authorization: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    auth_service: AuthServiceDep,
) -> LoginSession:
    rawtoken = authorization.credentials
    try:
        token = UUID(rawtoken)
    except Exception:
        raise UnauthorizedException(message="凭据无效")

    session_status, login_session = await auth_service.validate_login_session(
        access_token=token
    )
    match session_status:
        case LoginSessionStatus.EXPIRED:
            raise UnauthorizedException(message="凭据过期")
        case LoginSessionStatus.ACTIVE:
            pass
        case _:
            raise UnauthorizedException(message="会话无效")
    if login_session is None:
        raise UnauthorizedException(message="会话无效")

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
            raise ForbiddenException(message="权限不足")
        return role

    return Depends(check_role)


def get_problem_service(session: DbSessionDep) -> ProblemService:
    """获取题目服务实例"""
    problemset_repo = ProblemSetRepository()
    problem_repo = ProblemRepository()
    tag_repo = TagRepository()
    return ProblemService(
        session=session,
        problemset_repo=problemset_repo,
        problem_repo=problem_repo,
        tag_repo=tag_repo,
    )


ProblemServiceDep = Annotated[
    ProblemService,
    Depends(get_problem_service),
]


def get_user_service(session: DbSessionDep) -> UserService:
    """获取用户服务实例"""
    user_repo = UserRepository()
    return UserService(
        session=session,
        user_repo=user_repo,
    )


UserServiceDep = Annotated[
    UserService,
    Depends(get_user_service),
]