"""题目相关仓库类"""

from typing import Any
from uuid import UUID

from sqlalchemy import Text, cast
from sqlmodel import col, delete, desc, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import DBProblem, DBProblemSet, ProblemType
from app.repos.base import BaseRepository


class ProblemSetRepository(BaseRepository[DBProblemSet]):
    """题目集仓库"""
    
    def __init__(self) -> None:
        super().__init__(DBProblemSet)
    
    async def get_by_name(self, session: AsyncSession, name: str) -> DBProblemSet | None:
        """根据名称获取题目集"""
        return await self.get_by_field(session, "name", name.strip())
    
    async def exists_by_name(self, session: AsyncSession, name: str) -> bool:
        """检查题目集名称是否存在"""
        return await self.exists_by_field(session, "name", name.strip())
    
    async def list_with_count(self, session: AsyncSession) -> list[tuple[UUID, str, int]]:
        """获取题目集列表及其题目数量"""
        stmt = (
            select(
                col(DBProblemSet.id),
                col(DBProblemSet.name),
                func.count(col(DBProblem.id)).label("problem_count"),
            )
            .select_from(DBProblemSet)
            .outerjoin(DBProblem, col(DBProblem.problemset_id) == col(DBProblemSet.id))
            .group_by(col(DBProblemSet.id), col(DBProblemSet.name), col(DBProblemSet.created_at))
            .order_by(desc(col(DBProblemSet.created_at)))
        )
        results = await session.exec(stmt)
        return [(problemset_id, name, count or 0) for problemset_id, name, count in results]
    
    async def delete_all(self, session: AsyncSession) -> None:
        """删除所有题目集"""
        stmt = delete(DBProblemSet)
        await session.exec(stmt)


class ProblemRepository(BaseRepository[DBProblem]):
    """题目仓库"""
    
    def __init__(self) -> None:
        super().__init__(DBProblem)
    
    async def search(
        self,
        session: AsyncSession,
        kw: str | None = None,
        problemset_id: UUID | None = None,
        problem_type: ProblemType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[DBProblem]:
        """搜索题目"""
        stmt = select(DBProblem)
        
        # 应用过滤条件
        if problemset_id:
            stmt = stmt.where(DBProblem.problemset_id == problemset_id)
        if problem_type:
            stmt = stmt.where(DBProblem.type == problem_type)
        
        # 关键词搜索
        if kw and kw.strip():
            kw = kw.strip()
            if problem_type == ProblemType.SELECTIVE:
                stmt = stmt.where(
                    or_(
                        col(DBProblem.content).icontains(kw),
                        cast(col(DBProblem.details), Text).icontains(kw),
                    )
                )
            else:
                stmt = stmt.where(col(DBProblem.content).icontains(kw))
        
        # 分页
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        results = await session.exec(stmt)
        return list(results)
    
    async def count_by_filters(
        self,
        session: AsyncSession,
        problemset_id: UUID | None = None,
    ) -> int:
        """根据条件统计题目数量"""
        return await self.count(session, problemset_id=problemset_id)
    
    async def sample_by_problemset(
        self,
        session: AsyncSession,
        problemset_id: UUID,
        n: int = 20,
    ) -> list[DBProblem]:
        """随机抽样题目"""
        stmt = (
            select(DBProblem)
            .where(DBProblem.problemset_id == problemset_id)
            .order_by(func.random())
            .limit(n)
        )
        results = await session.exec(stmt)
        return list(results)
    
    async def delete_by_ids(self, session: AsyncSession, *problem_ids: UUID) -> None:
        """根据ID删除题目"""
        stmt = delete(DBProblem).where(col(DBProblem.id).in_(problem_ids))
        await session.exec(stmt)
    
    async def delete_by_problemset_id(self, session: AsyncSession, problemset_id: UUID) -> None:
        """根据题目集ID删除题目"""
        stmt = delete(DBProblem).where(col(DBProblem.problemset_id) == problemset_id)
        await session.exec(stmt)
    
    async def delete_all(self, session: AsyncSession) -> None:
        """删除所有题目"""
        stmt = delete(DBProblem)
        await session.exec(stmt)