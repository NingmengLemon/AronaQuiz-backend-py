import os
import uuid
from typing import AsyncGenerator

import dotenv
import pytest
from sqlmodel import select

from app.db.core import AsyncDatabaseCore
from app.db.models import TABLES, DBProblem
from app.db.operations import (
    ProblemSetCreateStatus,
    add_problems,
    create_problemset,
    delete_problems,
    delete_problemset,
    get_problem_count,
    query_problem,
    sample,
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
async def prepare_db(db: AsyncDatabaseCore) -> AsyncGenerator[uuid.UUID, None]:
    async with db.get_session() as session:
        await delete_problems(session)
        await session.commit()
        id_, _ = await create_problemset(session, "test")
        await session.commit()
    yield id_


async def test_add(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    async with db.get_session() as session:
        await add_problems(
            session,
            prepare_db,
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


async def test_multiadd(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
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
        await add_problems(session, prepare_db, *problems)
        await session.commit()
        assert (await get_problem_count(session)) == 1006


async def test_query_problem(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试查询单个问题功能"""
    async with db.get_session() as session:
        # 先添加一个问题
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="测试查询问题",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="正确答案"),
                    Option(is_correct=False, order=1, content="错误答案1"),
                    Option(is_correct=False, order=2, content="错误答案2"),
                ],
            ),
        )
        assert problem_ids is not None
        problem_id = problem_ids[0]
        await session.commit()

    async with db.get_session() as session:
        # 查询刚才添加的问题
        queried_problem = await query_problem(session, problem_id)
        assert queried_problem is not None
        assert queried_problem.content == "测试查询问题"
        assert queried_problem.type == ProblemType.single_select
        assert len(queried_problem.options) == 3
        assert queried_problem.options[0].content == "正确答案"
        assert queried_problem.options[0].is_correct is True

    async with db.get_session() as session:
        # 测试查询不存在的问题
        non_existent_id = uuid.uuid4()
        non_existent_problem = await query_problem(session, non_existent_id)
        assert non_existent_problem is None


async def test_search_problem(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试搜索问题功能"""
    async with db.get_session() as session:
        # 添加几个测试问题
        await add_problems(
            session,
            prepare_db,
            Problem(
                content="Python是一种编程语言",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="是的"),
                    Option(is_correct=False, order=1, content="不是"),
                ],
            ),
            Problem(
                content="Java也是一种编程语言",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="正确"),
                    Option(is_correct=False, order=1, content="错误"),
                ],
            ),
            Problem(
                content="什么是Python？",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="编程语言"),
                    Option(is_correct=False, order=1, content="动物"),
                ],
            ),
        )
        await session.commit()

    async with db.get_session() as session:
        # 搜索包含"Python"的问题
        results = await search_problem(session, "Python")
        assert len(results) == 2
        assert any("Python是一种编程语言" in p.content for p in results)
        assert any("什么是Python" in p.content for p in results)

        # 搜索包含"编程语言"的问题
        results = await search_problem(session, "编程语言")
        assert len(results) == 3  # 所有问题都包含"编程语言"

        # 测试分页
        results_page1 = await search_problem(session, "编程语言", page=1, page_size=2)
        results_page2 = await search_problem(session, "编程语言", page=2, page_size=2)
        assert len(results_page1) == 2
        assert len(results_page2) == 1
        assert results_page1 + results_page2 == results


async def test_delete_problems(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试删除问题功能"""
    async with db.get_session() as session:
        # 添加几个问题
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="问题1",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案1")],
            ),
            Problem(
                content="问题2",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案2")],
            ),
            Problem(
                content="问题3",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案3")],
            ),
        )
        assert problem_ids is not None
        await session.commit()
        assert await get_problem_count(session) == 3

    async with db.get_session() as session:
        # 删除第一个问题
        await delete_problems(session, problem_ids[0])
        await session.commit()
        assert await get_problem_count(session) == 2

        # 验证第一个问题已被删除
        deleted_problem = await query_problem(session, problem_ids[0])
        assert deleted_problem is None

        # 验证其他问题仍然存在
        remaining_problem = await query_problem(session, problem_ids[1])
        assert remaining_problem is not None
        assert remaining_problem.content == "问题2"

    async with db.get_session() as session:
        # 删除所有问题
        await delete_problems(session)
        await session.commit()
        assert await get_problem_count(session) == 0


async def test_sample_problems(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试随机抽样功能"""
    async with db.get_session() as session:
        # 添加多个问题
        problems = []
        for i in range(50):
            problems.append(
                Problem(
                    content=f"问题{i}",
                    type=ProblemType.single_select,
                    options=[Option(is_correct=True, order=0, content=f"答案{i}")],
                )
            )

        await add_problems(session, prepare_db, *problems)
        await session.commit()
        assert await get_problem_count(session) == 50

    async with db.get_session() as session:
        # 抽样10个问题
        sampled_problems = await sample(session, prepare_db, 10)
        assert len(sampled_problems) == 10

        # 验证抽样结果都是有效的问题
        for problem in sampled_problems:
            assert problem.content.startswith("问题")
            assert len(problem.options) == 1
            assert problem.options[0].is_correct is True

        # 测试抽样数量超过总数
        all_problems = await sample(session, prepare_db, 100)
        assert len(all_problems) == 50  # 应该返回所有问题


async def test_multi_select_problem(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试多选问题类型"""
    async with db.get_session() as session:
        # 添加一个多选题
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="以下哪些是编程语言？",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=True, order=0, content="Python"),
                    Option(is_correct=True, order=1, content="Java"),
                    Option(is_correct=False, order=2, content="HTML"),
                    Option(is_correct=True, order=3, content="C++"),
                ],
            ),
        )
        assert problem_ids is not None
        problem_id = problem_ids[0]
        await session.commit()

    async with db.get_session() as session:
        # 查询并验证多选题
        problem = await query_problem(session, problem_id)
        assert problem is not None
        assert problem.type == ProblemType.multi_select
        assert len(problem.options) == 4

        # 验证正确答案
        correct_options = [opt for opt in problem.options if opt.is_correct]
        assert len(correct_options) == 3
        correct_contents = {opt.content for opt in correct_options}
        assert correct_contents == {"Python", "Java", "C++"}


async def test_search_edge_cases(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试搜索边界情况"""
    async with db.get_session() as session:
        # 添加测试数据
        await add_problems(
            session,
            prepare_db,
            Problem(
                content="测试空字符串搜索test",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
        )
        await session.commit()

    async with db.get_session() as session:
        # 测试空关键词搜索
        empty_results = await search_problem(session, "")
        assert empty_results == []

        # 测试不存在的关键词
        no_results = await search_problem(session, "不存在的关键词")
        assert no_results == []

        # 测试特殊字符搜索
        special_char_results = await search_problem(session, "测试")
        assert len(special_char_results) == 1

        # 测试大小写不敏感搜索
        case_insensitive_results = await search_problem(session, "TEST")
        assert len(case_insensitive_results) == 1  # 应该能找到"测试"


async def test_problem_count(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    """测试问题计数功能"""
    async with db.get_session() as session:
        # 初始计数应为0
        assert await get_problem_count(session) == 0

        # 添加一个问题
        await add_problems(
            session,
            prepare_db,
            Problem(
                content="计数测试问题",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
        )
        await session.commit()
        assert await get_problem_count(session) == 1

        # 再添加一个问题
        await add_problems(
            session,
            prepare_db,
            Problem(
                content="另一个计数测试问题",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
        )
        await session.commit()
        assert await get_problem_count(session) == 2

        # 删除一个问题
        await delete_problems(session)
        await session.commit()
        assert await get_problem_count(session) == 0


async def test_problemset(db: AsyncDatabaseCore, prepare_db: uuid.UUID) -> None:
    async with db.get_session() as session:
        id_, status = await create_problemset(session, "test")
        assert id_ == prepare_db
        assert status == ProblemSetCreateStatus.already_exists
        await session.commit()

        id_, status = await create_problemset(session, "test2")
        assert id_ != prepare_db
        assert status == ProblemSetCreateStatus.success
        await session.commit()

        id__ = await delete_problemset(session, id_)
        assert id__ is not None
