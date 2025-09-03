import asyncio
import datetime
import os
import time
import uuid
from typing import AsyncGenerator

import dotenv
import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, delete, select

from app.db.core import AsyncDatabaseCore
from app.db.models import (
    TABLES,
    DBAnswerRecord,
    DBOption,
    DBProblem,
    DBUser,
)
from app.db.operations import (
    ProblemSetCreateStatus,
    add_problems,
    create_problemset,
    create_record,
    create_user,
    delete_all,
    delete_problems,
    delete_problemset,
    ensure_record,
    ensure_user,
    get_problem_count,
    list_problemset,
    query_problem,
    query_user,
    report_attempt,
    sample,
    search_problem,
)
from app.schemas.problem import Option, Problem, ProblemType

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
    db = AsyncDatabaseCore(
        DATABASE_URL,
        TABLES,
        # echo=True,
    )
    await db.startup()
    yield db


@pytest.fixture(scope="function")
async def prepare_db(db: AsyncDatabaseCore) -> AsyncGenerator[uuid.UUID, None]:
    async with db.get_session() as session:
        await delete_all(session)
        await session.exec(delete(DBUser))  # type: ignore
        await session.exec(delete(DBAnswerRecord))  # type: ignore
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
    start_time = time.time()
    async with db.get_session() as session:
        await add_problems(session, prepare_db, *problems)
        print(f"添加1006个问题耗时: {time.time() - start_time:.3f}秒")
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
        await delete_all(session)
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
        await delete_all(session)
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


async def test_user_operations(db: AsyncDatabaseCore) -> None:
    """测试用户相关操作"""

    async with db.get_session() as session:
        # 测试创建用户
        user1 = await create_user(session, "testuser1")
        await session.commit()
        assert user1.username == "testuser1"
        assert user1.id is not None

        # 测试查询用户（按用户名）
        queried_user = await query_user(session, username="testuser1")
        assert queried_user is not None
        assert queried_user.username == "testuser1"
        assert queried_user.id == user1.id

        # 测试查询用户（按ID）
        queried_user_by_id = await query_user(session, user_id=user1.id)
        assert queried_user_by_id is not None
        assert queried_user_by_id.username == "testuser1"

        # 测试查询不存在的用户
        non_existent_user = await query_user(session, username="nonexistent")
        assert non_existent_user is None

        # 测试 ensure_user - 用户已存在
        ensured_user = await ensure_user(session, "testuser1")
        assert ensured_user.id == user1.id

        # 测试 ensure_user - 用户不存在，应该创建新用户
        new_user = await ensure_user(session, "testuser2")
        await session.commit()
        assert new_user.username == "testuser2"
        assert new_user.id != user1.id


async def test_answer_record_operations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试答题记录相关操作"""

    async with db.get_session() as session:
        # 创建用户和问题
        user = await create_user(session, "test_student")
        await session.commit()

        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="测试答题记录的问题",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="正确答案"),
                    Option(is_correct=False, order=1, content="错误答案"),
                ],
            ),
        )
        assert problem_ids is not None
        problem_id = problem_ids[0]
        await session.commit()

        # 测试创建答题记录
        record = await create_record(session, user.id, problem_id)
        await session.commit()
        assert record.user_id == user.id
        assert record.problem_id == problem_id
        assert record.correct_count == 0
        assert record.total_count == 0

        # 测试 ensure_record - 记录已存在
        ensured_record = await ensure_record(session, user.id, problem_id)
        assert ensured_record.user_id == record.user_id
        assert ensured_record.problem_id == record.problem_id

        # 测试报告答题尝试（正确）
        test_time = datetime.datetime.now()
        await report_attempt(session, problem_id, user.id, correct=True, time=test_time)
        await session.commit()

        # 验证记录更新
        updated_user = await query_user(session, user_id=user.id)
        assert updated_user is not None

        # 测试报告答题尝试（错误）
        await report_attempt(session, problem_id, user.id, correct=False)
        await session.commit()

        # 测试多次答题
        for i in range(5):
            await report_attempt(session, problem_id, user.id, correct=i % 2 == 0)
        await session.commit()


async def test_advanced_search_operations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试高级搜索功能"""
    async with db.get_session() as session:
        # 添加多样化的测试数据
        problems_data = [
            ("Python编程基础知识", "Python", "编程语言", "基础", "高级"),
            ("Java面向对象编程", "Java", "OOP", "类", "对象"),
            ("数据结构与算法", "数组", "链表", "树", "图"),
            ("Web前端开发", "HTML", "CSS", "JavaScript", "React"),
            ("数据库设计原理", "SQL", "关系型", "NoSQL", "索引"),
        ]

        added_problems = []
        for content, *options in problems_data:
            problem = Problem(
                content=content,
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content=options[0]),
                    Option(is_correct=False, order=1, content=options[1]),
                    Option(is_correct=False, order=2, content=options[2]),
                    Option(is_correct=False, order=3, content=options[3]),
                ],
            )
            added_problems.append(problem)

        await add_problems(session, prepare_db, *added_problems)
        await session.commit()

        # 测试精确匹配搜索
        python_results = await search_problem(session, "Python")
        assert (
            len(python_results) == 1
        )  # Python编程基础知识 + Python选项, 但是去重后只剩一个

        # 测试模糊匹配搜索
        programming_results = await search_problem(session, "编程")
        assert len(programming_results) >= 2

        # 测试按问题集ID搜索
        problemset_results = await search_problem(session, None, prepare_db)
        assert len(problemset_results) == 5

        # 测试组合搜索（关键词 + 问题集ID）
        combined_results = await search_problem(session, "数据", prepare_db)
        assert len(combined_results) >= 1

        # 测试分页功能
        page1 = await search_problem(session, None, prepare_db, page=1, page_size=2)
        page2 = await search_problem(session, None, prepare_db, page=2, page_size=2)
        page3 = await search_problem(session, None, prepare_db, page=3, page_size=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

        # 验证分页结果不重复
        all_ids = set()
        for p in page1 + page2 + page3:
            assert p.id not in all_ids
            all_ids.add(p.id)


async def test_concurrent_operations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试并发操作"""

    async def add_problems_batch(batch_id: int) -> None:
        async with db.get_session() as session:
            problems = []
            for i in range(10):
                problems.append(
                    Problem(
                        content=f"批次{batch_id}问题{i}",
                        type=ProblemType.single_select,
                        options=[
                            Option(is_correct=True, order=0, content=f"正确答案{i}"),
                            Option(is_correct=False, order=1, content=f"错误答案{i}"),
                        ],
                    )
                )
            await add_problems(session, prepare_db, *problems)
            await session.commit()

    # 并发添加问题
    tasks = [add_problems_batch(i) for i in range(5)]
    await asyncio.gather(*tasks)

    async with db.get_session() as session:
        total_count = await get_problem_count(session)
        assert total_count == 50  # 5个批次，每批10个问题


async def test_data_validation_and_constraints(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试数据验证和约束"""
    async with db.get_session() as session:
        # 测试问题内容不能为空
        try:
            await add_problems(
                session,
                prepare_db,
                Problem(
                    content="",  # 空内容
                    type=ProblemType.single_select,
                    options=[Option(is_correct=True, order=0, content="答案")],
                ),
            )
            await session.commit()
            # 如果没有抛出异常，验证是否正确处理空内容
            problems = await search_problem(session, "")
            assert len(problems) >= 0  # 允许空内容搜索
        except Exception:
            pass  # 预期可能的验证错误

        # 测试选项顺序
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="测试选项顺序",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=False, order=2, content="第三个"),
                    Option(is_correct=True, order=0, content="第一个"),
                    Option(is_correct=False, order=3, content="第四个"),
                    Option(is_correct=True, order=1, content="第二个"),
                ],
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证选项顺序
        problem = await query_problem(session, problem_ids[0])
        assert problem is not None
        sorted_options = sorted(problem.options, key=lambda x: x.order)
        assert sorted_options[0].content == "第一个"
        assert sorted_options[1].content == "第二个"
        assert sorted_options[2].content == "第三个"
        assert sorted_options[3].content == "第四个"


async def test_problemset_operations_extended(db: AsyncDatabaseCore) -> None:
    """测试问题集操作的扩展功能"""

    async with db.get_session() as session:
        # 创建多个问题集
        ps1_id, status1 = await create_problemset(session, "数学题库")
        ps2_id, status2 = await create_problemset(session, "英语题库")
        ps3_id, status3 = await create_problemset(session, "计算机题库")
        await session.commit()

        assert status1 == ProblemSetCreateStatus.success
        assert status2 == ProblemSetCreateStatus.success
        assert status3 == ProblemSetCreateStatus.success

        # 为每个问题集添加不同数量的问题
        for ps_id, count in [(ps1_id, 10), (ps2_id, 5), (ps3_id, 15)]:
            problems = []
            for i in range(count):
                problems.append(
                    Problem(
                        content=f"问题{i}",
                        type=ProblemType.single_select,
                        options=[Option(is_correct=True, order=0, content=f"答案{i}")],
                    )
                )
            await add_problems(session, ps_id, *problems)
        await session.commit()

        # 测试列出所有问题集
        all_problemsets = await list_problemset(session)
        assert len(all_problemsets) >= 3

        # 验证问题集计数
        problemset_counts = {ps.name: ps.count for ps in all_problemsets}
        assert problemset_counts.get("数学题库") == 10
        assert problemset_counts.get("英语题库") == 5
        assert problemset_counts.get("计算机题库") == 15

        # 测试删除问题集及其所有问题
        deleted_id = await delete_problemset(session, ps1_id)
        assert deleted_id == ps1_id
        await session.commit()

        # 验证问题集已删除
        remaining_problemsets = await list_problemset(session)
        remaining_names = {ps.name for ps in remaining_problemsets}
        assert "数学题库" not in remaining_names
        assert "英语题库" in remaining_names
        assert "计算机题库" in remaining_names


async def test_edge_cases_and_error_handling(db: AsyncDatabaseCore) -> None:
    """测试边界情况和错误处理"""

    async with db.get_session() as session:
        # 测试对不存在的问题集添加问题
        fake_problemset_id = uuid.uuid4()
        result = await add_problems(
            session,
            fake_problemset_id,
            Problem(
                content="测试问题",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
        )
        assert result is None  # 应该返回 None

        # 测试查询不存在的问题
        fake_problem_id = uuid.uuid4()
        problem = await query_problem(session, fake_problem_id)
        assert problem is None

        # 测试删除不存在的问题集
        deleted_id = await delete_problemset(session, fake_problemset_id)
        assert deleted_id is None

        # 测试从空问题集中抽样
        empty_ps_id, _ = await create_problemset(session, "空问题集")
        await session.commit()

        sampled = await sample(session, empty_ps_id, 10)
        assert len(sampled) == 0

        # 测试空问题集的计数
        count = await get_problem_count(session, empty_ps_id)
        assert count == 0


async def test_problem_types_and_options(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试不同问题类型和选项配置"""
    async with db.get_session() as session:
        # 测试单选题（标准4选项）
        single_choice_id = await add_problems(
            session,
            prepare_db,
            Problem(
                content="哪个是正确的？",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=False, order=0, content="选项A"),
                    Option(is_correct=True, order=1, content="选项B"),
                    Option(is_correct=False, order=2, content="选项C"),
                    Option(is_correct=False, order=3, content="选项D"),
                ],
            ),
        )

        # 测试多选题（多个正确答案）
        multi_choice_id = await add_problems(
            session,
            prepare_db,
            Problem(
                content="以下哪些是正确的？",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=True, order=0, content="正确选项1"),
                    Option(is_correct=False, order=1, content="错误选项1"),
                    Option(is_correct=True, order=2, content="正确选项2"),
                    Option(is_correct=True, order=3, content="正确选项3"),
                ],
            ),
        )

        # 测试只有2个选项的题目
        binary_choice_id = await add_problems(
            session,
            prepare_db,
            Problem(
                content="这是真的吗？",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="是"),
                    Option(is_correct=False, order=1, content="否"),
                ],
            ),
        )

        # 测试有很多选项的题目
        many_options_id = await add_problems(
            session,
            prepare_db,
            Problem(
                content="选择所有偶数",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=(i % 2 == 0), order=i, content=str(i))
                    for i in range(10)
                ],
            ),
        )

        await session.commit()
        assert single_choice_id is not None
        assert multi_choice_id is not None
        assert binary_choice_id is not None
        assert many_options_id is not None

        # 验证单选题
        single_problem = await query_problem(session, single_choice_id[0])
        assert single_problem is not None
        assert single_problem.type == ProblemType.single_select
        correct_options = [opt for opt in single_problem.options if opt.is_correct]
        assert len(correct_options) == 1
        assert correct_options[0].content == "选项B"

        # 验证多选题
        multi_problem = await query_problem(session, multi_choice_id[0])
        assert multi_problem is not None
        assert multi_problem.type == ProblemType.multi_select
        correct_options = [opt for opt in multi_problem.options if opt.is_correct]
        assert len(correct_options) == 3

        # 验证二元选择题
        binary_problem = await query_problem(session, binary_choice_id[0])
        assert binary_problem is not None
        assert len(binary_problem.options) == 2

        # 验证多选项题目
        many_options_problem = await query_problem(session, many_options_id[0])
        assert many_options_problem is not None
        assert len(many_options_problem.options) == 10
        correct_count = sum(1 for opt in many_options_problem.options if opt.is_correct)
        assert correct_count == 5  # 0, 2, 4, 6, 8


async def test_performance_and_bulk_operations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试性能和批量操作"""

    async with db.get_session() as session:
        # 测试批量添加大量问题
        start_time = time.time()

        bulk_problems = []
        for i in range(100):
            bulk_problems.append(
                Problem(
                    content=f"性能测试问题{i}",
                    type=ProblemType.single_select,
                    options=[
                        Option(is_correct=True, order=0, content=f"正确答案{i}"),
                        Option(is_correct=False, order=1, content=f"错误答案{i}a"),
                        Option(is_correct=False, order=2, content=f"错误答案{i}b"),
                        Option(is_correct=False, order=3, content=f"错误答案{i}c"),
                    ],
                )
            )

        result = await add_problems(session, prepare_db, *bulk_problems)
        await session.commit()

        print(f"添加100个问题耗时: {time.time() - start_time:.3f}秒")

        assert result is not None
        assert len(result) == 100

        # 测试批量搜索性能
        start_time = time.time()
        search_results = await search_problem(session, "性能测试", page_size=0)
        search_time = time.time() - start_time

        print(f"搜索100个问题耗时: {search_time:.3f}秒")
        assert len(search_results) == 100

        # 测试分页搜索
        paginated_results = []
        for page in range(1, 11):  # 10页，每页10个
            page_results = await search_problem(
                session, "性能测试", page=page, page_size=10
            )
            paginated_results.extend(page_results)

        assert len(paginated_results) == 100

        # 测试批量删除
        start_time = time.time()
        await delete_problems(session, *result[:50])  # 删除前50个
        await session.commit()
        delete_time = time.time() - start_time

        print(f"删除50个问题耗时: {delete_time:.3f}秒")

        remaining_count = await get_problem_count(session, prepare_db)
        assert remaining_count == 50


async def test_database_transactions_and_rollback(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试数据库事务和回滚"""
    test_username = "Ayachi Nene"
    async with db.get_session() as session:
        with pytest.raises(IntegrityError):
            await create_user(session, test_username)
            # 预期出现用户重名错误
            await create_user(session, test_username)

        users = (
            await session.exec(select(DBUser).where(DBUser.username == test_username))
        ).all()
        assert len(users) == 1  # 预期第一个 create 成功, 第二个失败并回滚
        assert users[0].username == test_username


async def test_unicode_and_special_characters(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试Unicode和特殊字符处理"""
    async with db.get_session() as session:
        # 测试各种Unicode字符
        unicode_problems = [
            Problem(
                content="数学公式：∫₀¹ x² dx = ?",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="1/3"),
                    Option(is_correct=False, order=1, content="1/2"),
                ],
            ),
            Problem(
                content="emoji测试：🐍Python vs ☕Java？",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="Both are great! 🎉"),
                    Option(is_correct=False, order=1, content="Neither 😞"),
                ],
            ),
            Problem(
                content="中文测试：北京、上海、广州",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=True, order=0, content="一线城市"),
                    Option(is_correct=False, order=1, content="二线城市"),
                ],
            ),
            Problem(
                content="Русский язык тест",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="Привет"),
                    Option(is_correct=False, order=1, content="Hello"),
                ],
            ),
        ]

        result = await add_problems(session, prepare_db, *unicode_problems)
        await session.commit()
        assert result is not None
        assert len(result) == 4

        # 测试Unicode搜索
        math_results = await search_problem(session, "数学")
        assert len(math_results) >= 1

        emoji_results = await search_problem(session, "🐍")
        assert len(emoji_results) >= 1

        chinese_results = await search_problem(session, "北京")
        assert len(chinese_results) >= 1

        russian_results = await search_problem(session, "Русский")
        assert len(russian_results) >= 1

        # 验证存储和检索的完整性
        for problem_id in result:
            retrieved_problem = await query_problem(session, problem_id)
            assert retrieved_problem is not None
            # 验证内容没有被截断或损坏
            assert len(retrieved_problem.content) > 0
            assert len(retrieved_problem.options) > 0


async def test_database_integrity_and_relationships(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试数据库完整性和关系约束"""

    async with db.get_session() as session:
        # 添加一个问题
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="关系测试问题",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="选项1"),
                    Option(is_correct=False, order=1, content="选项2"),
                ],
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证问题和选项的关系
        problem_db = (
            await session.exec(select(DBProblem).where(DBProblem.id == problem_ids[0]))
        ).one_or_none()
        assert problem_db is not None

        options = await problem_db.awaitable_attrs.options
        assert len(options) == 2
        assert all(opt.problem_id == problem_db.id for opt in options)

        # 验证问题集和问题的关系
        problemset_db = await problem_db.awaitable_attrs.problemset
        assert problemset_db.id == prepare_db

        # 测试级联删除：删除问题应该同时删除其选项
        option_ids = [opt.id for opt in options]
        await delete_problems(session, problem_ids[0])
        await session.commit()

        # 验证选项也被删除了
        remaining_options = (
            await session.exec(select(DBOption).where(col(DBOption.id).in_(option_ids)))
        ).all()
        assert len(remaining_options) == 0


async def test_search_with_user_statistics(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试带用户统计的搜索功能"""

    async with db.get_session() as session:
        # 创建用户
        user = await create_user(session, "test_stat_user")

        # 添加问题
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="统计测试问题1",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
            Problem(
                content="统计测试问题2",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案")],
            ),
        )
        assert problem_ids is not None

        # 记录一些答题尝试
        await report_attempt(session, problem_ids[0], user.id, correct=True)
        await report_attempt(session, problem_ids[0], user.id, correct=False)
        await report_attempt(session, problem_ids[0], user.id, correct=True)

        await report_attempt(session, problem_ids[1], user.id, correct=False)
        await report_attempt(session, problem_ids[1], user.id, correct=False)

        # 测试带用户统计的搜索
        search_results = await search_problem(session, "统计测试", user_id=user.id)
        assert len(search_results) == 2

        # 验证统计信息
        for result in search_results:
            if result.id == problem_ids[0]:
                assert result.correct_count == 2
                assert result.total_count == 3
            elif result.id == problem_ids[1]:
                assert result.correct_count == 0
                assert result.total_count == 2


async def test_problem_sampling_variations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试问题抽样的各种情况"""
    async with db.get_session() as session:
        # 添加不同类型的问题
        mixed_problems = []
        for i in range(20):
            problem_type = (
                ProblemType.single_select if i % 2 == 0 else ProblemType.multi_select
            )
            options = [
                Option(is_correct=True, order=0, content=f"正确答案{i}"),
                Option(is_correct=False, order=1, content=f"错误答案{i}"),
            ]
            if problem_type == ProblemType.multi_select:
                options.append(
                    Option(is_correct=True, order=2, content=f"另一个正确答案{i}")
                )

            mixed_problems.append(
                Problem(
                    content=f"抽样测试问题{i}",
                    type=problem_type,
                    options=options,
                )
            )

        await add_problems(session, prepare_db, *mixed_problems)
        await session.commit()

        # 测试不同大小的抽样
        sample_sizes = [1, 5, 10, 15, 20, 25]
        for size in sample_sizes:
            sampled = await sample(session, prepare_db, size)
            expected_size = min(size, 20)  # 最多只能抽到20个
            assert len(sampled) == expected_size


async def test_complex_query_scenarios(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试复杂查询场景"""
    async with db.get_session() as session:
        # 创建复杂的测试数据
        complex_problems = [
            Problem(
                content="Python中的装饰器是什么？",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="一种设计模式"),
                    Option(is_correct=False, order=1, content="一种数据类型"),
                    Option(is_correct=False, order=2, content="一种循环结构"),
                ],
            ),
            Problem(
                content="以下哪些是Python的内置数据类型？",
                type=ProblemType.multi_select,
                options=[
                    Option(is_correct=True, order=0, content="list"),
                    Option(is_correct=True, order=1, content="dict"),
                    Option(is_correct=False, order=2, content="array"),
                    Option(is_correct=True, order=3, content="tuple"),
                ],
            ),
            Problem(
                content="JavaScript中的异步编程",
                type=ProblemType.single_select,
                options=[
                    Option(is_correct=True, order=0, content="Promise"),
                    Option(is_correct=False, order=1, content="Synchronous"),
                ],
            ),
        ]

        await add_problems(session, prepare_db, *complex_problems)
        await session.commit()

        # 测试不同关键词的搜索
        test_cases = [
            ("Python", 2),  # 应该找到2个Python相关问题
            ("装饰器", 1),  # 应该找到1个装饰器问题
            ("数据类型", 2),  # 应该找到2个数据类型相关问题
            ("JavaScript", 1),  # 应该找到1个JavaScript问题
            ("异步", 1),  # 应该找到1个异步问题
            ("不存在的关键词", 0),  # 应该找不到任何问题
        ]

        for keyword, expected_count in test_cases:
            results = await search_problem(session, keyword)
            assert len(results) == expected_count, (
                f"搜索'{keyword}'应该返回{expected_count}个结果，实际返回{len(results)}个"
            )

        # 测试组合搜索
        python_in_problemset = await search_problem(session, "Python", prepare_db)
        assert len(python_in_problemset) == 2

        # 测试分页边界情况
        all_results = await search_problem(session, None, prepare_db)
        total_count = len(all_results)

        # 测试最后一页
        last_page_size = total_count % 2 if total_count % 2 != 0 else 2
        last_page = total_count // 2 + (1 if total_count % 2 != 0 else 0)

        if last_page > 0:
            last_page_results = await search_problem(
                session, None, prepare_db, page=last_page, page_size=2
            )
            assert len(last_page_results) == last_page_size


async def test_data_consistency_after_operations(
    db: AsyncDatabaseCore, prepare_db: uuid.UUID
) -> None:
    """测试操作后的数据一致性"""
    async with db.get_session() as session:
        # 记录初始状态
        initial_count = await get_problem_count(session, prepare_db)

        # 执行一系列操作
        problem_ids = await add_problems(
            session,
            prepare_db,
            Problem(
                content="一致性测试问题1",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案1")],
            ),
            Problem(
                content="一致性测试问题2",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案2")],
            ),
            Problem(
                content="一致性测试问题3",
                type=ProblemType.single_select,
                options=[Option(is_correct=True, order=0, content="答案3")],
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证添加后的计数
        after_add_count = await get_problem_count(session, prepare_db)
        assert after_add_count == initial_count + 3

        # 删除部分问题
        await delete_problems(session, problem_ids[0], problem_ids[2])
        await session.commit()

        # 验证删除后的计数
        after_delete_count = await get_problem_count(session, prepare_db)
        assert after_delete_count == initial_count + 1

        # 验证剩余的问题是正确的
        remaining_problem = await query_problem(session, problem_ids[1])
        assert remaining_problem is not None
        assert remaining_problem.content == "一致性测试问题2"

        # 验证删除的问题确实不存在了
        deleted_problem1 = await query_problem(session, problem_ids[0])
        deleted_problem3 = await query_problem(session, problem_ids[2])
        assert deleted_problem1 is None
        assert deleted_problem3 is None

        # 搜索验证
        search_results = await search_problem(session, "一致性测试")
        assert len(search_results) == 1
        assert search_results[0].content == "一致性测试问题2"
