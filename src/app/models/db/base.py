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
    # 将 __tablename__ 标注为 ClassVar
    # 用基类中的一个 type: ignore 避免子类中的多个 MyPy 警告
    # 并将表注册到自定义的 registry 中, 而不是默认的 SQLModel registry, 以便于管理
    if TYPE_CHECKING:
        __tablename__: ClassVar[str]  # type: ignore


class BaseHasId(Base):
    id: UUID = Field(default_factory=uuid7, primary_key=True)


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore
    # 其他异步属性和方法可以通过继承 AsyncAttrs, 并将其作为模型的泛型参数进行标注
    # 但并不影响运行时行为, 因为 sa 已经实现了这些功能,
    # 只是 awaitable_attrs 没有类型标注
