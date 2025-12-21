from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Generic, ParamSpec, Protocol, cast
from uuid import UUID

from sqlalchemy.orm import QueryableAttribute
from sqlmodel.ext.asyncio.session import AsyncSession
from typing_extensions import TypeVar

P = ParamSpec("P")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class AsyncCallable(Protocol[P, T_co]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T_co]: ...


class VoidType(Enum):
    VOID = type("_VOID", (), {})


SessionGetterType = Callable[[], AsyncSession]


def queryable(o: T) -> QueryableAttribute[T]:
    return cast(QueryableAttribute, o)


IdTypeT = TypeVar("IdTypeT", default=UUID)


class ObjHasId(Protocol, Generic[IdTypeT]):
    id: IdTypeT
