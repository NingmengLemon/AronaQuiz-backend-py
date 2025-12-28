from collections.abc import Sequence

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.tag import DBTag
from app.repos.base import BaseRepository


class TagRepository(BaseRepository[DBTag]):
    def __init__(self) -> None:
        super().__init__(DBTag)

    async def get_or_create_tags(
        self, session: AsyncSession, tag_names: Sequence[str]
    ) -> list[DBTag]:
        """获取或创建标签

        会创建不存在的标签, 谨慎使用"""
        if not tag_names:
            return []

        existing_tags = await self.get_by_names(session, tag_names)
        existing_tag_names = {tag.name for tag in existing_tags}

        new_tags = []
        for name in tag_names:
            if name not in existing_tag_names:
                new_tags.append(DBTag(name=name))

        if new_tags:
            session.add_all(new_tags)
            await session.flush()  # Flush to assign IDs to new tags
            for tag in new_tags:
                await session.refresh(tag)  # Refresh to load all fields, including id

        return existing_tags + new_tags

    async def get_existing_tags(
        self, session: AsyncSession, tag_names: Sequence[str]
    ) -> list[DBTag]:
        """只获取已存在的标签, 不创建新标签"""
        if not tag_names:
            return []

        return await self.get_by_names(session, tag_names)

    async def get_by_names(
        self, session: AsyncSession, tag_names: Sequence[str]
    ) -> list[DBTag]:
        statement = select(DBTag).where(col(DBTag.name).in_(tag_names))
        result = await session.exec(statement)
        return list(result.all())
