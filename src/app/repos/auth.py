"""会话相关仓库类"""

from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.auth import LoginSession, LoginSessionStatus
from app.repos.base import BaseRepository


class AuthRepository(BaseRepository[LoginSession]):
    """认证与会话仓库"""

    def __init__(self) -> None:
        super().__init__(LoginSession)

    async def get_by_access_token(
        self, session: AsyncSession, access_token: UUID
    ) -> LoginSession | None:
        """根据访问令牌获取会话"""
        return await self.get_by_field(session, "access_token", access_token)

    async def get_by_refresh_token_hash(
        self, session: AsyncSession, refresh_token_hash: str
    ) -> LoginSession | None:
        """根据刷新令牌哈希获取会话"""
        return await self.get_by_field(
            session, "refresh_token_hash", refresh_token_hash
        )

    async def get_active_sessions_by_user(
        self, session: AsyncSession, user_id: UUID
    ) -> list[LoginSession]:
        """获取用户的活跃会话"""
        stmt = select(LoginSession).where(
            LoginSession.user_id == user_id,
            LoginSession.status == LoginSessionStatus.ACTIVE,
        )
        results = await session.exec(stmt)
        return list(results)

    async def revoke_all_user_sessions(
        self, session: AsyncSession, user_id: UUID
    ) -> None:
        """撤销用户的所有会话"""
        stmt = select(LoginSession).where(
            LoginSession.user_id == user_id,
            LoginSession.status == LoginSessionStatus.ACTIVE,
        )
        results = await session.exec(stmt)
        for login_session in results:
            login_session.status = LoginSessionStatus.REVOKED
            session.add(login_session)
