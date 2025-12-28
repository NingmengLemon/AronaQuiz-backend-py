"""标签业务逻辑服务层"""

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.exceptions import APIException
from app.models.db.problem import DBProblem, DBProblemSet
from app.models.db.tag import DBTag
from app.models.dto.code import BusinessCode
from app.repos.tag import TagRepository


class TagService:
    """标签业务服务"""

    def __init__(
        self,
        session: AsyncSession,
        tag_repo: TagRepository,
    ) -> None:
        self.session = session
        self.tag_repo = tag_repo

    async def list_tags(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[DBTag]:
        """获取标签列表，支持关键词搜索和分页"""
        statement = select(DBTag)

        if keyword:
            # 使用模糊搜索
            statement = statement.where(col(DBTag.name).icontains(keyword))

        # 添加分页
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)

        result = await self.session.exec(statement)
        return list(result.all())

    async def get_tag_by_id(self, tag_id: UUID) -> DBTag | None:
        """根据ID获取标签"""
        return await self.tag_repo.get_by_id(self.session, tag_id)

    async def get_tag_by_name(self, name: str) -> DBTag | None:
        """根据名称获取标签"""
        tags = await self.tag_repo.get_by_names(self.session, [name])
        return tags[0] if tags else None

    async def create_tag(self, name: str) -> DBTag:
        """创建新标签"""
        # 检查标签名称是否已存在
        existing = await self.get_tag_by_name(name)
        if existing:
            raise APIException(
                status_code=409,
                code=BusinessCode.CONFLICT,
                message=f"标签 '{name}' 已存在",
            )

        # 创建新标签
        tag = DBTag(name=name)
        created = await self.tag_repo.create(self.session, tag)
        return created

    async def update_tag(self, tag_id: UUID, new_name: str) -> DBTag | None:
        """更新标签名称"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return None

        # 检查新名称是否与其他标签冲突
        existing = await self.get_tag_by_name(new_name)
        if existing and existing.id != tag_id:
            raise APIException(
                status_code=409,
                code=BusinessCode.CONFLICT,
                message=f"标签 '{new_name}' 已存在",
            )

        tag.name = new_name
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: UUID) -> bool:
        """删除标签"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return False

        await self.tag_repo.delete(self.session, tag)
        return True

    async def get_tag_problems(self, tag_id: UUID) -> list[DBProblem]:
        """获取使用该标签的所有题目"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return []

        # 通过relationship获取题目
        await self.session.refresh(tag, ["problems"])
        return tag.problems

    async def get_tag_problemsets(self, tag_id: UUID) -> list[DBProblemSet]:
        """获取使用该标签的所有题目集"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return []

        # 通过relationship获取题目集
        await self.session.refresh(tag, ["problemsets"])
        return tag.problemsets

    async def count_tags(self, keyword: str | None = None) -> int:
        """统计标签数量"""
        statement = select(DBTag)

        if keyword:
            statement = statement.where(col(DBTag.name).ilike(f"%{keyword}%"))

        result = await self.session.exec(statement)
        return len(list(result.all()))

    async def get_or_create_tags(self, tag_names: Sequence[str]) -> list[DBTag]:
        """获取或创建标签（批量）"""
        return await self.tag_repo.get_or_create_tags(self.session, tag_names)

    async def get_popular_tags(self, limit: int = 10) -> list[tuple[DBTag, int]]:
        """获取最常用的标签（按使用次数排序）"""
        # 这里需要复杂的查询来统计每个标签的使用次数
        # 暂时返回空列表，后续可以优化实现
        return []
