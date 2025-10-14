from collections.abc import Awaitable, Callable
from enum import Enum
from typing import ParamSpec, Protocol, TypeVar

from sqlmodel.ext.asyncio.session import AsyncSession

P = ParamSpec("P")
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class AsyncCallable(Protocol[P, T_co]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T_co]: ...


class VoidType(Enum):
    VOID = type("_VOID", (), {})


SessionGetterType = Callable[[], AsyncSession]
