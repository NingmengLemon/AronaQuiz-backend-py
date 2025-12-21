"""会话业务逻辑服务层"""

import logging
from datetime import timedelta
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.models.db.auth import LoginSession, LoginSessionStatus
from app.repos.auth import AuthRepository
from app.repos.user import UserRepository
from app.utils.misc import utcnow
from app.utils.security import hash, verify

logger = logging.getLogger("uvicorn.error")


class AuthService:
    """会话业务服务"""

    def __init__(
        self,
        session: AsyncSession,
        auth_repo: AuthRepository,
        user_repo: UserRepository,
    ) -> None:
        self.session = session
        self.auth_repo = auth_repo
        self.user_repo = user_repo

    async def login(
        self,
        *,
        password: str,
        username: str | None = None,
        user_id: UUID | None = None,
        email: str | None = None,
    ) -> tuple[UUID, UUID] | None:
        """用户登录"""
        # 构建查询条件
        if user_id is not None:
            user = await self.user_repo.get_by_user_id(self.session, user_id)
        elif username is not None:
            user = await self.user_repo.get_by_username(self.session, username)
        elif email is not None:
            user = await self.user_repo.get_by_email(self.session, email)
        else:
            raise ValueError("missing user identifier")

        if user is None:
            return None

        if not await verify(user.password_hash, password):
            return None

        refresh_token = uuid4()
        new_session = LoginSession(
            user_id=user.id,
            refresh_token_hash=await hash(str(refresh_token)),
        )
        created_session = await self.auth_repo.create(self.session, new_session)
        return created_session.access_token, refresh_token

    async def query_login_session(
        self,
        *,
        access_token: UUID | None = None,
        session_id: UUID | None = None,
    ) -> LoginSession | None:
        """查询登录会话"""
        if access_token is not None:
            return await self.auth_repo.get_by_access_token(self.session, access_token)
        elif session_id is not None:
            return await self.auth_repo.get_by_id(self.session, session_id)
        else:
            raise ValueError("missing login session identifier")

    async def validate_login_session(
        self,
        access_token: UUID,
    ) -> tuple[LoginSessionStatus, LoginSession | None]:
        """验证登录会话"""
        login_session = await self.auth_repo.get_by_access_token(
            self.session, access_token
        )
        if login_session is None:
            return LoginSessionStatus.INVALID, None

        if login_session.status == LoginSessionStatus.EXPIRED:
            return LoginSessionStatus.EXPIRED, None

        now = utcnow()
        if login_session.expires_at <= now:
            if login_session.status == LoginSessionStatus.ACTIVE:
                login_session.status = LoginSessionStatus.EXPIRED
                login_session.last_active = now
                await self.auth_repo.update(self.session, login_session)
            return LoginSessionStatus.EXPIRED, None

        if login_session.status == LoginSessionStatus.ACTIVE:
            login_session.last_active = now
            await self.auth_repo.update(self.session, login_session)
            return LoginSessionStatus.ACTIVE, login_session

        return LoginSessionStatus.INVALID, None

    async def refresh_access_token(
        self,
        access_token: UUID,
        refresh_token: UUID,
        rotate: bool = True,
    ) -> tuple[UUID, UUID] | None:
        """刷新访问令牌 - 实现令牌轮换

        传入当前的 access_token 和 refresh_token, 验证通过后返回新的令牌对.
        验证包括检查 refresh_token 是否过期.
        如果 rotate 为 True, 则生成新的 refresh_token 并轮换.
        如果 rotate 为 False, 则保持 refresh_token 不变但仍返回原始 refresh_token."""
        login_session = await self.auth_repo.get_by_access_token(
            self.session, access_token
        )
        if login_session is None:
            return None

        if not await verify(login_session.refresh_token_hash, str(refresh_token)):
            return None

        # 检查刷新令牌是否过期
        now = utcnow()
        if login_session.refresh_token_expires_at <= now:
            return None

        # 生成新的访问令牌
        new_access_token = uuid4()
        login_session.access_token = new_access_token
        login_session.last_renewal = now
        login_session.expires_at = now + timedelta(
            days=get_settings().auth.access_token_lifetime_days
        )

        # 处理刷新令牌轮换
        if rotate:
            # 轮换刷新令牌
            new_refresh_token = uuid4()
            login_session.refresh_token_hash = await hash(str(new_refresh_token))
            login_session.refresh_token_expires_at = now + timedelta(
                days=get_settings().auth.refresh_token_lifetime_days
            )
        else:
            # 保持刷新令牌不变，但返回原始刷新令牌
            new_refresh_token = refresh_token

        await self.auth_repo.update(self.session, login_session)
        return new_access_token, new_refresh_token

    async def logout(
        self,
        access_token: UUID,
    ) -> bool:
        """用户登出"""
        login_session = await self.auth_repo.get_by_access_token(
            self.session, access_token
        )
        if login_session is None:
            return False

        login_session.status = LoginSessionStatus.REVOKED
        await self.auth_repo.update(self.session, login_session)
        return True

    async def revoke_all_user_sessions(
        self,
        user_id: UUID,
    ) -> None:
        """撤销用户的所有会话"""
        await self.auth_repo.revoke_all_user_sessions(self.session, user_id)
