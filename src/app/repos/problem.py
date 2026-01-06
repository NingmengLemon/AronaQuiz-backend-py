"""题目相关仓库类"""

from uuid import UUID

from sqlalchemy import Text
from sqlmodel import and_, cast, col, delete, desc, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import DBProblem, DBProblemSet, ProblemType
from app.repos.base import BaseRepository


class ProblemSetRepository(BaseRepository[DBProblemSet]):
    """题目集仓库"""

    def __init__(self) -> None:
        super().__init__(DBProblemSet)

    async def get_by_owner_id_and_name(
        self, session: AsyncSession, owner_id: UUID, name: str
    ) -> DBProblemSet | None:
        """根据所有者ID和名称获取题目集"""
        stmt = select(DBProblemSet).where(
            DBProblemSet.owner_id == owner_id, DBProblemSet.name == name.strip()
        )
        result = await session.exec(stmt)
        return result.first()

    async def list_with_count(
        self, session: AsyncSession
    ) -> list[tuple[UUID, str, int]]:
        """获取题目集列表及其题目数量"""
        stmt = (
            select(
                col(DBProblemSet.id),
                col(DBProblemSet.name),
                func.count(col(DBProblem.id)).label("problem_count"),
            )
            .select_from(DBProblemSet)
            .outerjoin(DBProblem, col(DBProblem.problemset_id) == col(DBProblemSet.id))
            .group_by(
                col(DBProblemSet.id),
                col(DBProblemSet.name),
                col(DBProblemSet.created_at),
            )
            .order_by(desc(col(DBProblemSet.created_at)))
        )
        results = await session.exec(stmt)
        return [
            (problemset_id, name, count or 0) for problemset_id, name, count in results
        ]

    async def search(
        self,
        session: AsyncSession,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[tuple[UUID, str, int]]:
        """搜索题目集及其题目数量"""
        stmt = (
            select(
                col(DBProblemSet.id),
                col(DBProblemSet.name),
                func.count(col(DBProblem.id)).label("problem_count"),
            )
            .select_from(DBProblemSet)
            .outerjoin(DBProblem, col(DBProblem.problemset_id) == col(DBProblemSet.id))
            .group_by(
                col(DBProblemSet.id),
                col(DBProblemSet.name),
                col(DBProblemSet.description),
                col(DBProblemSet.created_at),
            )
        )

        # 关键词搜索
        if keyword and keyword.strip():
            keyword = keyword.strip()
            stmt = stmt.where(col(DBProblemSet.name).icontains(keyword))

        # 分页
        stmt = stmt.order_by(desc(col(DBProblemSet.created_at)))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        results = await session.exec(stmt)
        return [
            (problemset_id, name, count or 0) for problemset_id, name, count in results
        ]

    async def count_by_keyword(
        self, session: AsyncSession, keyword: str | None = None
    ) -> int:
        """根据关键词统计题目集数量"""
        stmt = select(func.count(col(DBProblemSet.id))).select_from(DBProblemSet)

        if keyword and keyword.strip():
            keyword = keyword.strip()
            stmt = stmt.where(col(DBProblemSet.name).icontains(keyword))

        result = await session.exec(stmt)
        return result.one()

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
        kws: list[str] | None = None,
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
        if kws:
            filters = []
            for kw in kws:
                kw = kw.strip()
                match problem_type:
                    case ProblemType.SELECTIVE:
                        filters.append(
                            or_(
                                col(DBProblem.content).icontains(kw),
                                cast(DBProblem.details, Text).icontains(kw),
                            )
                        )
                    case _:
                        filters.append(col(DBProblem.content).icontains(kw))
            stmt = stmt.where(and_(*filters))
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

    async def delete_by_problemset_id(
        self, session: AsyncSession, problemset_id: UUID
    ) -> None:
        """根据题目集ID删除题目"""
        stmt = delete(DBProblem).where(col(DBProblem.problemset_id) == problemset_id)
        await session.exec(stmt)

    async def delete_all(self, session: AsyncSession) -> None:
        """删除所有题目"""
        stmt = delete(DBProblem)
        await session.exec(stmt)
