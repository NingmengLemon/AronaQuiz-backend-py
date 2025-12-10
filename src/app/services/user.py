"""用户业务逻辑服务层"""

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.user import DBUser, UserRole
from app.repos.user import UserRepository
from app.utils.db import in_transaction, in_readonly_transaction
from app.utils.security import hash


class UserService:
    """用户业务服务"""
    
    def __init__(self) -> None:
        self.user_repo = UserRepository()
    
    async def query_user(
        self,
        session: AsyncSession,
        *,
        username: str | None = None,
        user_id: UUID | None = None,
    ) -> DBUser | None:
        """查询用户"""
        if not ((username is None) ^ (user_id is None)):
            raise ValueError("choose from username and user_id")
        
        if username:
            return await self.user_repo.get_by_username(session, username)
        else:
            # 此时user_id一定不为None，因为上面的检查
            return await self.user_repo.get_by_user_id(session, user_id)  # type: ignore
    
    async def create_user(
        self,
        session: AsyncSession,
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
        return await self.user_repo.create(session, user)
    
    async def check_user_exists(
        self,
        session: AsyncSession,
        username: str | None = None,
        email: str | None = None,
        nickname: str | None = None,
    ) -> dict[str, bool]:
        """检查用户是否存在"""
        result = {}
        if username:
            result["username"] = await self.user_repo.exists_by_username(session, username)
        if email:
            result["email"] = await self.user_repo.exists_by_email(session, email)
        if nickname:
            result["nickname"] = await self.user_repo.exists_by_nickname(session, nickname)
        return result


# 创建服务实例
user_service = UserService()

# 导出带事务装饰器的方法
query_user = in_readonly_transaction()(user_service.query_user)
create_user = in_transaction()(user_service.create_user)