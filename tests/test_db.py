import os
from typing import Any, AsyncGenerator

import dotenv
import pytest
from sqlmodel import delete, select

from app.db.core import AsyncDatabaseCore
from app.db.models import TABLES, DBProblem
from app.db.operations import (
    add_problems,
    delete_problems,
    get_problem_count,
    query_problem,
    search_problem,
)
from app.schemas.sheet import Option, Problem, ProblemType

dotenv.load_dotenv()

DB_NAME = "hdusp2_test"


@pytest.fixture(scope="module")
async def db() -> AsyncGenerator[AsyncDatabaseCore, None]:
    # username = os.getenv("DB_USER")
    # password = os.getenv("DB_PASSWORD")
    # host = os.getenv("DB_HOST")
    # port = int((os.getenv("DB_PORT") or 5432))
    # DATABASE_URL = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"
    if os.path.exists(f := f"data/{DB_NAME}.db"):
        os.remove(f)
    DATABASE_URL = f"sqlite+aiosqlite:///data/{DB_NAME}.db"
    db = AsyncDatabaseCore(DATABASE_URL, TABLES, echo=True)
    await db.startup()
    yield db


@pytest.fixture(scope="function")
async def clear_db(db: AsyncDatabaseCore) -> AsyncGenerator[None, None]:
    async with db.get_session() as session:
        await delete_problems(session)
        await session.commit()
    yield


async def test_add(db: AsyncDatabaseCore, clear_db: None) -> None:
    async with db.get_session() as session:
        await add_problems(
            session,
            Problem(
                content="114514 + 1919810 = ?",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="2034324"),
                    Option(is_correct=False, order=1, content="45450721"),
                    Option(is_correct=False, order=2, content="0x0d000721"),
                    Option(is_correct=False, order=3, content="undefined"),
                ],
            ),
        )
        await session.commit()

    async with db.get_session() as session:
        problems = (await session.exec(select(DBProblem))).all()
        assert len(problems) == 1
        problem = problems[0]
        options = await problem.awaitable_attrs.options
        assert len(options) == 4
        assert options[0].is_correct == 1
        assert options[0].content == "2034324"
        print(problem)


async def test_multiadd(db: AsyncDatabaseCore, clear_db: None) -> None:
    with open("data/example_data.csv", "r", encoding="utf-8", errors="replace") as fp:
        sheet = fp.readlines()
    problems: list[Problem] = []
    for idx, raw_problem in enumerate(sheet):
        if idx == 0:
            continue
        _, type_, content, answ, _, _, _, _, a, b, c, d, _, _ = (
            raw_problem.strip().split(",")
        )
        problems.append(
            Problem(
                content=content,
                type=(
                    ProblemType.multi_select
                    if type_ == "多选题"
                    else ProblemType.single_select
                ),
                options=[
                    Option(
                        content=opcontent,
                        order=ord(order) - ord("A"),
                        is_correct=order in answ,
                    )
                    for order, opcontent in zip("ABCD", filter(None, [a, b, c, d]))
                ],
            )
        )
    async with db.get_session() as session:
        await add_problems(session, *problems)
        await session.commit()
        assert (await get_problem_count(session)) == 1006
