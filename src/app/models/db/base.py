from typing import TYPE_CHECKING, ClassVar

from sqlalchemy.orm import registry
from sqlmodel import SQLModel

arona_registry = registry()
arona_metadata = arona_registry.metadata


class Base(SQLModel, registry=arona_registry, metadata=arona_metadata):
    if TYPE_CHECKING:
        __tablename__: ClassVar[str]  # type: ignore
