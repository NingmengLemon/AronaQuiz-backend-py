"""题目业务逻辑服务层"""

import re
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import DBProblem, DBProblemSet, ProblemType
from app.models.dto.request import ProblemSubmit
from app.models.dto.response import ProblemResponse, ProblemSetResponse
from app.repos.problem import ProblemRepository, ProblemSetRepository
from app.repos.tag import TagRepository

TAG_NAME_CONSTRAINT_REGEX = re.compile(r"^[\w\-]{1,30}$")


class ProblemService:
    """题目业务服务"""

    def __init__(
        self,
        session: AsyncSession,
        problemset_repo: ProblemSetRepository,
        problem_repo: ProblemRepository,
        tag_repo: TagRepository,
    ) -> None:
        self.session = session
        self.problem_set_repo = problemset_repo
        self.problem_repo = problem_repo
        self.tag_repo = tag_repo

    async def create_problemset(
        self,
        owner_id: UUID,
        name: str,
        is_public: bool,
        tags: list[str] | None = None,
        description: str = "",
    ) -> tuple[UUID, str]:
        """创建题目集"""
        name = name.strip()
        # 检查标签合规性
        if tags:
            for tag in tags:
                if not TAG_NAME_CONSTRAINT_REGEX.match(tag):
                    raise ValueError(f"Invalid tag name: {tag}")

        # 检查是否已存在同名题目集（在同一用户下）
        existing = await self.problem_set_repo.get_by_owner_id_and_name(
            self.session, owner_id, name
        )
        if existing:
            return existing.id, "ALREADY_EXISTS"

        # 获取或创建标签
        db_tags = []
        if tags:
            db_tags = await self.tag_repo.get_or_create_tags(self.session, tags)

        # 创建新题目集
        problemset = DBProblemSet(
            owner_id=owner_id,
            name=name,
            description=description,
            is_public=is_public,
        )
        if db_tags:
            problemset.tags = db_tags
        created = await self.problem_set_repo.create(self.session, problemset)
        return created.id, "SUCCESS"

    async def add_problems(
        self,
        problemset_id: UUID,
        *problems: ProblemSubmit,
    ) -> list[UUID] | None:
        """添加题目到题目集"""
        # 检查题目集是否存在
        problemset = await self.problem_set_repo.get_by_id(self.session, problemset_id)
        if not problemset:
            return None

        # 添加题目
        added_problems = []
        for problem_data in problems:
            if problem_data.type == ProblemType.SELECTIVE:
                # 获取题目标签
                db_tags = []
                if problem_data.tags:
                    # 只使用已存在的标签
                    db_tags = await self.tag_repo.get_existing_tags(self.session, problem_data.tags)
                    # 检查是否有不存在的标签
                    existing_tag_names = {tag.name for tag in db_tags}
                    missing_tags = [tag for tag in problem_data.tags if tag not in existing_tag_names]
                    if missing_tags:
                        raise ValueError(f"以下标签不存在: {', '.join(missing_tags)}")

                problem = DBProblem(
                    type=problem_data.type,
                    content=problem_data.content,
                    details=problem_data.details,
                    problemset_id=problemset.id,
                )
                if db_tags:
                    problem.tags = db_tags
                created = await self.problem_repo.create(self.session, problem)
                added_problems.append(created.id)

        return added_problems

    async def search_problems(
        self,
        kw: str | None = None,
        problemset_id: UUID | None = None,
        problem_type: ProblemType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ProblemResponse]:
        """搜索题目"""
        problems = await self.problem_repo.search(
            self.session,
            kw=kw,
            problemset_id=problemset_id,
            problem_type=problem_type,
            page=page,
            page_size=page_size,
        )
        return [
            ProblemResponse.model_validate(p, from_attributes=True) for p in problems
        ]

    async def get_problem_count(
        self,
        problemset_id: UUID | None = None,
    ) -> int:
        """获取题目数量"""
        return await self.problem_repo.count_by_filters(
            self.session, problemset_id=problemset_id
        )

    async def sample_problems(
        self,
        problemset_id: UUID,
        n: int = 20,
    ) -> list[ProblemResponse]:
        """随机抽样题目"""
        problems = await self.problem_repo.sample_by_problemset(
            self.session, problemset_id, n
        )
        return [
            ProblemResponse.model_validate(p, from_attributes=True) for p in problems
        ]

    async def list_problemsets(self) -> list[ProblemSetResponse]:
        """获取题目集列表"""
        results = await self.problem_set_repo.list_with_count(self.session)
        return [
            ProblemSetResponse(id=problemset_id, name=name, count=count)
            for problemset_id, name, count in results
        ]

    async def search_problemsets(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[ProblemSetResponse]:
        """搜索题目集"""
        results = await self.problem_set_repo.search(
            self.session,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        return [
            ProblemSetResponse(id=problemset_id, name=name, count=count)
            for problemset_id, name, count in results
        ]

    async def get_problemset_count(self, keyword: str | None = None) -> int:
        """获取题目集数量"""
        return await self.problem_set_repo.count_by_keyword(
            self.session, keyword=keyword
        )

    async def delete_problems(
        self,
        *problem_ids: UUID,
    ) -> None:
        """删除题目"""
        await self.problem_repo.delete_by_ids(self.session, *problem_ids)

    async def delete_problemset(
        self,
        problemset_id: UUID,
    ) -> UUID | None:
        """删除题目集及其所有题目"""
        problemset = await self.problem_set_repo.get_by_id(self.session, problemset_id)
        if not problemset:
            return None

        # 删除题目集中的所有题目
        await self.problem_repo.delete_by_problemset_id(self.session, problemset_id)

        # 删除题目集
        await self.problem_set_repo.delete(self.session, problemset)

        return problemset_id

    async def delete_all_problems(self) -> None:
        """删除所有题目和题目集"""
        # 删除所有题目
        await self.problem_repo.delete_all(self.session)
        # 删除所有题目集
        await self.problem_set_repo.delete_all(self.session)
