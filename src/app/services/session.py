"""会话业务逻辑服务层"""

import logging
from datetime import timedelta
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.session import (
    ACCESS_TOKEN_LIFETIME,
    LoginSession,
    LoginSessionStatus,
)
from app.models.db.user import DBUser
from app.repos.session import SessionRepository
from app.repos.user import UserRepository
from app.utils.db import in_transaction, in_readonly_transaction
from app.utils.misc import utcnow
from app.utils.security import sha256, verify

logger = logging.getLogger("uvicorn.error")


class SessionService:
    """会话业务服务"""
    
    def __init__(self) -> None:
        self.session_repo = SessionRepository()
        self.user_repo = UserRepository()
    
    async def login(
        self,
        session: AsyncSession,
        *,
        password: str,
        username: str | None = None,
        user_id: UUID | None = None,
        email: str | None = None,
    ) -> tuple[UUID, UUID] | None:
        """用户登录"""
        # 构建查询条件
        if user_id is not None:
            user = await self.user_repo.get_by_user_id(session, user_id)
        elif username is not None:
            user = await self.user_repo.get_by_username(session, username)
        elif email is not None:
            user = await self.user_repo.get_by_email(session, email)
        else:
            raise ValueError("missing user identifier")
        
        if user is None:
            return None
        
        if not await verify(user.password_hash, password):
            return None
        
        refresh_token = uuid4()
        new_session = LoginSession(
            user_id=user.id,
            refresh_token_hash=await sha256(refresh_token),
        )
        created_session = await self.session_repo.create(session, new_session)
        return created_session.access_token, refresh_token
    
    async def query_login_session(
        self,
        session: AsyncSession,
        *,
        access_token: UUID | None = None,
        session_id: UUID | None = None,
    ) -> LoginSession | None:
        """查询登录会话"""
        if access_token is not None:
            return await self.session_repo.get_by_access_token(session, access_token)
        elif session_id is not None:
            return await self.session_repo.get_by_id(session, session_id)
        else:
            raise ValueError("missing login session identifier")
    
    async def validate_login_session(
        self,
        session: AsyncSession,
        access_token: UUID,
    ) -> tuple[LoginSessionStatus, LoginSession | None]:
        """验证登录会话"""
        login_session = await self.session_repo.get_by_access_token(session, access_token)
        if login_session is None:
            return LoginSessionStatus.INVALID, None
        
        if login_session.status == LoginSessionStatus.EXPIRED:
            return LoginSessionStatus.EXPIRED, None
        
        now = utcnow()
        if login_session.expires_at <= now:
            if login_session.status == LoginSessionStatus.ACTIVE:
                login_session.status = LoginSessionStatus.EXPIRED
                await self.session_repo.update(session, login_session)
            return LoginSessionStatus.EXPIRED, None
        
        if login_session.status == LoginSessionStatus.ACTIVE:
            login_session.last_active = now
            await self.session_repo.update(session, login_session)
            return LoginSessionStatus.ACTIVE, login_session
        
        return LoginSessionStatus.INVALID, None
    
    async def refresh_access_token(
        self,
        session: AsyncSession,
        access_token: UUID,
        refresh_token: UUID,
    ) -> tuple[UUID, UUID | None] | None:
        """刷新访问令牌"""
        login_session = await self.session_repo.get_by_access_token(session, access_token)
        if login_session is None:
            return None
        
        refresh_token_hash = await sha256(refresh_token)
        if login_session.refresh_token_hash != refresh_token_hash:
            return None
        
        new_access_token = uuid4()
        login_session.access_token = new_access_token
        login_session.last_renewal = utcnow()
        login_session.expires_at = login_session.last_renewal + timedelta(
            days=ACCESS_TOKEN_LIFETIME
        )
        
        await self.session_repo.update(session, login_session)
        return new_access_token, None
    
    async def logout(
        self,
        session: AsyncSession,
        access_token: UUID,
    ) -> bool:
        """用户登出"""
        login_session = await self.session_repo.get_by_access_token(session, access_token)
        if login_session is None:
            return False
        
        login_session.status = LoginSessionStatus.REVOKED
        await self.session_repo.update(session, login_session)
        return True
    
    async def revoke_all_user_sessions(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> None:
        """撤销用户的所有会话"""
        await self.session_repo.revoke_all_user_sessions(session, user_id)


# 创建服务实例
session_service = SessionService()

# 导出带事务装饰器的方法
login = in_transaction()(session_service.login)
query_login_session = in_readonly_transaction()(session_service.query_login_session)
validate_login_session = in_transaction()(session_service.validate_login_session)
refresh_access_token = in_transaction()(session_service.refresh_access_token)
logout = in_transaction()(session_service.logout)
revoke_all_user_sessions = in_transaction()(session_service.revoke_all_user_sessions)