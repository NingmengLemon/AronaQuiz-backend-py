from app.schemas.sheet import Option, Problem

from .models import DBOption, DBProblem


def dboption2pydoption(o: DBOption) -> Option:
    return Option(id=o.id, content=o.content, order=o.order, is_correct=o.is_correct)


async def dbproblem2pydproblem(p: DBProblem) -> Problem:
    return Problem(
        id=p.id,
        content=p.content,
        options=[dboption2pydoption(o) for o in await p.awaitable_attrs.options],
        type=p.type,
    )


# 因为 async sqlmodel 的关系属性是懒加载的所以需要这么一下
