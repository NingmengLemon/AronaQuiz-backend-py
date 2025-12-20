"""用户业务逻辑服务层"""

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import validate_email
from pydantic_core import PydanticCustomError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.user import DBUser, UserRole
from app.repos.user import UserRepository
from app.utils.security import hash

USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_\-]{3,16}$", re.U | re.I)
NICKNAME_REGEX = re.compile(
    r"^[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AFa-zA-Z0-9\u00C0-\u00FF_-]{2,16}$",
    re.U | re.I,
)

USER_FIELD_MAP: dict[str, Any] = {
    "email": DBUser.email,
    "username": DBUser.username,
    "nickname": DBUser.nickname,
}


class UserService:
    """用户业务服务"""

    def __init__(self, session: AsyncSession, user_repo: UserRepository) -> None:
        self.user_repo = user_repo
        self.session = session

    async def query_user(
        self,
        *,
        username: str | None = None,
        user_id: UUID | None = None,
    ) -> DBUser | None:
        """查询用户"""
        if not ((username is None) ^ (user_id is None)):
            raise ValueError("choose from username and user_id")

        if username:
            return await self.user_repo.get_by_username(self.session, username)
        else:
            # 此时user_id一定不为None，因为上面的检查
            return await self.user_repo.get_by_user_id(self.session, user_id)  # type: ignore

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        nickname: str,
        role: UserRole = UserRole.USER,
    ) -> DBUser:
        """创建用户"""
        hashed_passwd = await hash(password)
        user = DBUser(
            email=email,
            username=username,
            password_hash=hashed_passwd,
            nickname=nickname,
            role=role,
        )
        return await self.user_repo.create(self.session, user)

    async def check_userinfo_availability(
        self,
        field: str,
        value: str,
    ) -> Literal["ok", "conflict", "invalid"]:
        """检查用户信息可用性"""
        if field not in USER_FIELD_MAP:
            return "invalid"

        # 验证格式
        match field:
            case "email":
                try:
                    validate_email(value)
                except PydanticCustomError:
                    return "invalid"
            case "username":
                if USERNAME_REGEX.match(value) is None:
                    return "invalid"
            case "nickname":
                if NICKNAME_REGEX.match(value) is None:
                    return "invalid"

        # 检查数据库中是否已存在
        if field == "email":
            user = await self.user_repo.get_by_email(session=self.session, email=value)
        elif field == "username":
            user = await self.user_repo.get_by_username(
                session=self.session, username=value
            )
        elif field == "nickname":
            user = await self.user_repo.get_by_field(
                session=self.session, field="nickname", value=value
            )
        else:
            user = None

        if user is not None:
            return "conflict"
        return "ok"

    async def check_multiple_userinfo_availability(
        self,
        username: str | None = None,
        email: str | None = None,
        nickname: str | None = None,
    ) -> dict[str, Literal["ok", "conflict", "invalid"]]:
        """检查多个用户信息可用性"""
        results = {}

        if username:
            results["username"] = await self.check_userinfo_availability(
                "username", username
            )
        if email:
            results["email"] = await self.check_userinfo_availability("email", email)
        if nickname:
            results["nickname"] = await self.check_userinfo_availability(
                "nickname", nickname
            )

        return results
