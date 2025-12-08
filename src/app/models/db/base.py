from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from sqlalchemy.ext.asyncio.session import AsyncAttrs as _AsyncAttrs
from sqlalchemy.orm import registry
from sqlmodel import SQLModel

T = TypeVar("T")

arona_registry = registry()
arona_metadata = arona_registry.metadata


class Base(SQLModel, registry=arona_registry, metadata=arona_metadata):
    if TYPE_CHECKING:
        __tablename__: ClassVar[str]  # type: ignore


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore
