"""基础仓库类，提供通用的数据库操作"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.base import BaseHasId

ModelT = TypeVar("ModelT", bound=BaseHasId)


class BaseRepository(Generic[ModelT]):
    """基础仓库类，提供通用的CRUD操作"""

    def __init__(self, model_class: type[ModelT]):
        self.model_class = model_class

    async def get_by_id(self, session: AsyncSession, id: UUID) -> ModelT | None:
        """根据ID获取实体"""
        return (
            await session.exec(
                select(self.model_class).where(self.model_class.id == id)
            )
        ).one_or_none()  # type: ignore

    async def get_by_field(
        self, session: AsyncSession, field: str, value: Any
    ) -> ModelT | None:
        """根据字段获取实体"""
        return (
            await session.exec(
                select(self.model_class).where(
                    getattr(self.model_class, field) == value
                )
            )
        ).one_or_none()

    async def exists_by_field(
        self, session: AsyncSession, field: str, value: Any
    ) -> bool:
        """检查字段值是否存在"""
        result = await session.exec(
            select(self.model_class).where(getattr(self.model_class, field) == value)
        )
        return result.first() is not None

    async def create(self, session: AsyncSession, entity: ModelT) -> ModelT:
        """创建实体"""
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def update(self, session: AsyncSession, entity: ModelT) -> ModelT:
        """更新实体"""
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: ModelT) -> None:
        """删除实体"""
        await session.delete(entity)
        await session.flush()

    async def count(self, session: AsyncSession, **filters: Any) -> int:
        """统计数量"""
        stmt = select(func.count()).select_from(self.model_class)
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model_class, field) == value)
        return (await session.exec(stmt)).one()
