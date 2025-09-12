from enum import Enum
from typing import Awaitable, ParamSpec, Protocol, TypeVar

P = ParamSpec("P")
T_co = TypeVar("T_co", covariant=True)


class AsyncCallable(Protocol[P, T_co]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T_co]: ...


class VoidType(Enum):
    VOID = type("_VOID", (), {})
