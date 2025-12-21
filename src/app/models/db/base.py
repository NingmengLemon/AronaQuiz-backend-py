from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio.session import AsyncAttrs as _AsyncAttrs
from sqlalchemy.orm import registry
from sqlmodel import Field, SQLModel

from app.utils.uuid7 import uuid7

T = TypeVar("T")

arona_registry = registry()
arona_metadata = arona_registry.metadata


class Base(SQLModel, registry=arona_registry, metadata=arona_metadata):
    if TYPE_CHECKING:
        __tablename__: ClassVar[str]  # type: ignore


class BaseHasId(Base):
    id: UUID = Field(default_factory=uuid7, primary_key=True)


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore
