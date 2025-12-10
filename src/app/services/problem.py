"""题目业务逻辑服务层"""

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import DBProblem, DBProblemSet, ProblemType
from app.models.dto.request import ProblemSubmit
from app.models.dto.response import ProblemResponse, ProblemSetResponse
from app.repos.problem import ProblemRepository, ProblemSetRepository
from app.utils.db import in_transaction, in_readonly_transaction


class ProblemService:
    """题目业务服务"""
    
    def __init__(self) -> None:
        self.problem_set_repo = ProblemSetRepository()
        self.problem_repo = ProblemRepository()
    
    async def create_problemset(self, session: AsyncSession, name: str) -> tuple[UUID, str]:
        """创建题目集"""
        name = name.strip()
        
        # 检查是否已存在
        existing = await self.problem_set_repo.get_by_name(session, name)
        if existing:
            return existing.id, "ALREADY_EXISTS"
        
        # 创建新题目集
        problemset = DBProblemSet(name=name)
        created = await self.problem_set_repo.create(session, problemset)
        return created.id, "SUCCESS"
    
    async def add_problems(
        self,
        session: AsyncSession,
        problemset_id: UUID,
        *problems: ProblemSubmit,
    ) -> list[UUID] | None:
        """添加题目到题目集"""
        # 检查题目集是否存在
        problemset = await self.problem_set_repo.get_by_id(session, problemset_id)
        if not problemset:
            return None
        
        # 添加题目
        added_problems = []
        for problem_data in problems:
            if problem_data.type == ProblemType.SELECTIVE:
                problem = DBProblem.model_validate(
                    problem_data,
                    update={"problemset_id": problemset.id, "problemset": problemset},
                )
                created = await self.problem_repo.create(session, problem)
                added_problems.append(created.id)
        
        return added_problems
    
    async def search_problems(
        self,
        session: AsyncSession,
        kw: str | None = None,
        problemset_id: UUID | None = None,
        problem_type: ProblemType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ProblemResponse]:
        """搜索题目"""
        problems = await self.problem_repo.search(
            session,
            kw=kw,
            problemset_id=problemset_id,
            problem_type=problem_type,
            page=page,
            page_size=page_size,
        )
        return [ProblemResponse.model_validate(p, from_attributes=True) for p in problems]
    
    async def get_problem_count(
        self,
        session: AsyncSession,
        problemset_id: UUID | None = None,
    ) -> int:
        """获取题目数量"""
        return await self.problem_repo.count_by_filters(session, problemset_id=problemset_id)
    
    async def sample_problems(
        self,
        session: AsyncSession,
        problemset_id: UUID,
        n: int = 20,
    ) -> list[ProblemResponse]:
        """随机抽样题目"""
        problems = await self.problem_repo.sample_by_problemset(session, problemset_id, n)
        return [ProblemResponse.model_validate(p, from_attributes=True) for p in problems]
    
    async def list_problemsets(self, session: AsyncSession) -> list[ProblemSetResponse]:
        """获取题目集列表"""
        results = await self.problem_set_repo.list_with_count(session)
        return [
            ProblemSetResponse(id=problemset_id, name=name, count=count)
            for problemset_id, name, count in results
        ]
    
    async def delete_problems(
        self,
        session: AsyncSession,
        *problem_ids: UUID,
    ) -> None:
        """删除题目"""
        await self.problem_repo.delete_by_ids(session, *problem_ids)
    
    async def delete_problemset(
        self,
        session: AsyncSession,
        problemset_id: UUID,
    ) -> UUID | None:
        """删除题目集及其所有题目"""
        problemset = await self.problem_set_repo.get_by_id(session, problemset_id)
        if not problemset:
            return None
        
        # 删除题目集中的所有题目
        await self.problem_repo.delete_by_problemset_id(session, problemset_id)
        
        # 删除题目集
        await self.problem_set_repo.delete(session, problemset)
        
        return problemset_id
    
    async def delete_all_problems(self, session: AsyncSession) -> None:
        """删除所有题目和题目集"""
        # 删除所有题目
        await self.problem_repo.delete_all(session)
        # 删除所有题目集
        await self.problem_set_repo.delete_all(session)


# 创建服务实例
problem_service = ProblemService()

# 导出带事务装饰器的方法
create_problemset = in_transaction()(problem_service.create_problemset)
add_problems = in_transaction()(problem_service.add_problems)
search_problems = in_readonly_transaction()(problem_service.search_problems)
get_problem_count = in_readonly_transaction()(problem_service.get_problem_count)
sample_problems = in_readonly_transaction()(problem_service.sample_problems)
list_problemsets = in_readonly_transaction()(problem_service.list_problemsets)
delete_problems = in_transaction()(problem_service.delete_problems)
delete_problemset = in_transaction()(problem_service.delete_problemset)
delete_all_problems = in_transaction()(problem_service.delete_all_problems)