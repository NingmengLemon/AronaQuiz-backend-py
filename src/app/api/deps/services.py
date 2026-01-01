from typing import Annotated

from fastapi import Depends

from app.repos.auth import AuthRepository
from app.repos.problem import ProblemRepository, ProblemSetRepository
from app.repos.tag import TagRepository
from app.repos.user import UserRepository
from app.services.auth import AuthService
from app.services.problem import ProblemService
from app.services.tag import TagService
from app.services.user import UserService

from .db import DbSessionDep


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


def get_tag_service(session: DbSessionDep) -> TagService:
    """获取标签服务实例"""
    tag_repo = TagRepository()
    return TagService(
        session=session,
        tag_repo=tag_repo,
    )


TagServiceDep = Annotated[
    TagService,
    Depends(get_tag_service),
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
