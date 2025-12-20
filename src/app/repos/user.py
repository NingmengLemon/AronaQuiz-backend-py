"""用户相关仓库类"""

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.user import DBUser
from app.repos.base import BaseRepository


class UserRepository(BaseRepository[DBUser]):
    """用户仓库"""

    def __init__(self) -> None:
        super().__init__(DBUser)

    async def get_by_username(
        self, session: AsyncSession, username: str
    ) -> DBUser | None:
        """根据用户名获取用户"""
        return await self.get_by_field(session, "username", username)

    async def get_by_email(self, session: AsyncSession, email: str) -> DBUser | None:
        """根据邮箱获取用户"""
        return await self.get_by_field(session, "email", email)

    async def get_by_user_id(
        self, session: AsyncSession, user_id: UUID
    ) -> DBUser | None:
        """根据用户ID获取用户"""
        return await self.get_by_id(session, user_id)

    async def exists_by_username(self, session: AsyncSession, username: str) -> bool:
        """检查用户名是否存在"""
        return await self.exists_by_field(session, "username", username)

    async def exists_by_email(self, session: AsyncSession, email: str) -> bool:
        """检查邮箱是否存在"""
        return await self.exists_by_field(session, "email", email)

    async def exists_by_nickname(self, session: AsyncSession, nickname: str) -> bool:
        """检查昵称是否存在"""
        return await self.exists_by_field(session, "nickname", nickname)
