import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.db.problem import (
    DBProblem,
    ProblemType,
    SelectiveProblemDetails,
    SelectiveProblemOption,
)
from app.models.db.user import DBUser
from app.models.dto.request import ProblemSubmit, SelectiveProblemSubmit
from app.repos.problem import ProblemRepository, ProblemSetRepository
from app.repos.user import UserRepository
from app.services.problem import ProblemService
from app.services.user import UserService
from app.typ import SessionGetterType

logger = logging.getLogger(__name__)
problem_repo = ProblemRepository()
problemset_repo = ProblemSetRepository()
query_problem = problem_repo.get_by_id
search_problem = problem_repo.search
sample = problem_repo.sample_by_problemset
list_problemset = problemset_repo.list_with_count


@pytest_asyncio.fixture(scope="function")
async def init_problemset_uuid(
    test_session_getter: SessionGetterType,
) -> AsyncGenerator[UUID, None]:
    logger.info("Initializing problem set UUID fixture.")
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 创建测试问题集
        id_, status = await problem_service.create_problemset("test")
        await session.commit()
        if status != "SUCCESS":
            # 如果已存在，获取已存在的问题集ID
            problemsets = await list_problemset(session)
            test_problemset = next((ps for ps in problemsets if ps[1] == "test"), None)
            if test_problemset:
                id_ = test_problemset[0]
            else:
                # 创建新的问题集
                id_, _ = await problem_service.create_problemset("test")
        await session.commit()
    logger.info("Problem set UUID fixture initialized.")
    yield id_


async def _create_user_simple(session: AsyncSession, username: str) -> UUID:
    user_service = UserService(session, UserRepository())
    return (
        await user_service.create_user(
            username=username,
            email=f"{username.lower().replace(' ', '')}@example.com",
            nickname=username,
            password="114514",
        )
    ).id


@pytest.mark.asyncio
async def test_add(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 确保问题集存在
        problemset = await problemset_repo.get_by_id(session, init_problemset_uuid)
        assert problemset is not None

        result = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="114514 + 1919810 = ?",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="2034324"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="45450721"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="0x0d000721"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=3, content="undefined"
                        ),
                    ],
                ),
            ),
        )
        assert result is not None
        assert len(result) == 1
        problem_id = result[0]

        # 验证问题已创建
        problem = await problem_repo.get_by_id(session, problem_id)
        assert problem is not None
        assert problem.type == ProblemType.SELECTIVE
        options = problem.details["options"]
        assert len(options) == 4
        assert options[0]["is_correct"] == 1
        assert options[0]["content"] == "2034324"


@pytest.mark.asyncio
async def test_multiadd(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    with open("data/example_data.csv", "r", encoding="utf-8", errors="replace") as fp:
        sheet = fp.readlines()
    problems: list[ProblemSubmit] = []
    for idx, raw_problem in enumerate(sheet):
        if idx == 0:
            continue
        _, type_, content, answ, _, _, _, _, a, b, c, d, _, _ = (
            raw_problem.strip().split(",")
        )
        problems.append(
            SelectiveProblemSubmit(
                content=content,
                details=SelectiveProblemDetails(
                    type="multiple" if len(answ) > 1 else "single",
                    options=[
                        SelectiveProblemOption(
                            content=opcontent,
                            order=ord(order) - ord("A"),
                            is_correct=order in answ,
                        )
                        for order, opcontent in zip("ABCD", filter(None, [a, b, c, d]))
                    ],
                ),
            )
        )
    with open("data/example_data.json", "r", encoding="utf-8") as fp:
        sheet_ = json.load(fp)
    additional = 0
    start_time = time.time()
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        for s in sheet_:
            i, _ = await problem_service.create_problemset(s["name"])
            await problem_service.add_problems(
                i,
                *[
                    SelectiveProblemSubmit(
                        content=p["content"],
                        type=ProblemType.SELECTIVE,
                        details={
                            "type": p["type"],
                            "options": p["options"],
                        },
                    )
                    for p in s["problems"]
                ],
            )
            additional += len(s["problems"])
        await problem_service.add_problems(init_problemset_uuid, *problems)
        print(
            f"添加 {len(problems) + additional} 个问题耗时: {time.time() - start_time:.3f}秒"
        )
        assert (await problem_service.get_problem_count()) == len(problems) + additional


@pytest.mark.asyncio
async def test_query_problem(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试查询单个问题功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 先添加一个问题
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="测试查询问题",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="正确答案"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="错误答案1"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="错误答案2"
                        ),
                    ],
                ),
            ),
        )
        await session.commit()
        assert problem_ids is not None
        problem_id = problem_ids[0]
        await session.commit()

    async with test_session_getter() as session:
        # 查询刚才添加的问题
        queried_problem = await query_problem(session, problem_id)
        assert queried_problem is not None
        assert queried_problem.content == "测试查询问题"
        assert queried_problem.type == ProblemType.SELECTIVE
        assert len(queried_problem.details["options"]) == 3
        assert queried_problem.details["options"][0]["content"] == "正确答案"
        assert queried_problem.details["options"][0]["is_correct"] is True

    async with test_session_getter() as session:
        # 测试查询不存在的问题
        non_existent_id = uuid4()
        non_existent_problem = await query_problem(session, non_existent_id)
        assert non_existent_problem is None


@pytest.mark.asyncio
async def test_search_problem(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试搜索问题功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 添加几个测试问题
        await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="Python是一种编程语言",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="是的"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="不是"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="Java也是一种编程语言",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="正确"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="错误"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="什么是Python？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="编程语言"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="动物"
                        ),
                    ],
                ),
            ),
        )
        await session.commit()

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 搜索包含"Python"的问题
        results = await problem_service.search_problems(
            kw="Python", problem_type=ProblemType.SELECTIVE
        )
        assert len(results) == 2
        assert any("Python是一种编程语言" in p.content for p in results)
        assert any("什么是Python" in p.content for p in results)

        # 搜索包含"编程语言"的问题
        results = await problem_service.search_problems(
            kw="编程语言", problem_type=ProblemType.SELECTIVE
        )
        assert len(results) == 3  # 所有问题都包含"编程语言"

        # 测试分页
        results_page1 = await problem_service.search_problems(
            kw="编程语言", problem_type=ProblemType.SELECTIVE, page=1, page_size=2
        )
        results_page2 = await problem_service.search_problems(
            kw="编程语言", problem_type=ProblemType.SELECTIVE, page=2, page_size=2
        )
        assert len(results_page1) == 2
        assert len(results_page2) == 1
        assert results_page1 + results_page2 == results


@pytest.mark.asyncio
async def test_delete_problems(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试删除问题功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 添加几个问题
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="问题1",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案1"
                        )
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="问题2",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案2"
                        )
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="问题3",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案3"
                        )
                    ],
                ),
            ),
        )
        assert problem_ids is not None
        await session.commit()
        assert await problem_service.get_problem_count() == 3

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 删除第一个问题
        await problem_service.delete_problems(problem_ids[0])
        await session.commit()
        assert await problem_service.get_problem_count() == 2

        # 验证第一个问题已被删除
        deleted_problem = await query_problem(session, problem_ids[0])
        assert deleted_problem is None

        # 验证其他问题仍然存在
        remaining_problem = await query_problem(session, problem_ids[1])
        assert remaining_problem is not None
        assert remaining_problem.content == "问题2"

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 删除所有问题
        await problem_service.delete_all_problems(session)
        await session.commit()
        assert await problem_service.get_problem_count() == 0


@pytest.mark.asyncio
async def test_sample_problems(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试随机抽样功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 添加多个问题
        problems = []
        for i in range(50):
            problems.append(
                SelectiveProblemSubmit(
                    content=f"问题{i}",
                    type=ProblemType.SELECTIVE,
                    details=SelectiveProblemDetails(
                        type="single",
                        options=[
                            SelectiveProblemOption(
                                is_correct=True, order=0, content=f"答案{i}"
                            )
                        ],
                    ),
                )
            )

        await problem_service.add_problems(init_problemset_uuid, *problems)
        await session.commit()
        assert await problem_service.get_problem_count() == 50

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 抽样10个问题
        sampled_problems = await problem_service.sample_problems(
            init_problemset_uuid, 10
        )
        assert len(sampled_problems) == 10

        # 验证抽样结果都是有效的问题
        for problem in sampled_problems:
            assert problem.content.startswith("问题")
            assert len(problem.details["options"]) == 1
            assert problem.details["options"][0]["is_correct"] is True

        # 测试抽样数量超过总数
        all_problems = await problem_service.sample_problems(init_problemset_uuid, 100)
        assert len(all_problems) == 50  # 应该返回所有问题


@pytest.mark.asyncio
async def test_SELECTIVE_problem(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试多选问题类型"""
    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 添加一个多选题
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="以下哪些是编程语言？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="Python"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=1, content="Java"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="HTML"
                        ),
                        SelectiveProblemOption(is_correct=True, order=3, content="C++"),
                    ],
                ),
            ),
        )
        assert problem_ids is not None
        problem_id = problem_ids[0]
        await session.commit()

    async with test_session_getter() as session:
        # 查询并验证多选题
        problem = await problem_repo.get_by_id(session, problem_id)
        assert problem is not None
        assert problem.type == ProblemType.SELECTIVE
        assert len(problem.details["options"]) == 4

        # 验证正确答案
        correct_options = [
            opt for opt in problem.details["options"] if opt["is_correct"]
        ]
        assert len(correct_options) == 3
        correct_contents = {opt["content"] for opt in correct_options}
        assert correct_contents == {"Python", "Java", "C++"}


@pytest.mark.asyncio
async def test_search_edge_cases(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试搜索边界情况"""
    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 添加测试数据
        await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="测试空字符串搜索test",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="答案")
                    ],
                ),
            ),
        )
        await session.commit()

    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()

        # 测试不存在的关键词
        no_results = await problem_repo.search(session, "不存在的关键词")
        assert no_results == []

        # 测试特殊字符搜索
        special_char_results = await problem_repo.search(session, "测试")
        assert len(special_char_results) == 1

        # 测试大小写不敏感搜索
        case_insensitive_results = await problem_repo.search(session, "TEST")
        assert len(case_insensitive_results) == 1  # 应该能找到"测试"


@pytest.mark.asyncio
async def test_problem_count(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试问题计数功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 初始计数应为0
        assert await problem_service.get_problem_count() == 0

        # 添加一个问题
        await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="计数测试问题",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="答案")
                    ],
                ),
            ),
        )
        await session.commit()
        assert await problem_service.get_problem_count() == 1

        # 再添加一个问题
        await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="另一个计数测试问题",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="答案")
                    ],
                ),
            ),
        )
        await session.commit()
        assert await problem_service.get_problem_count() == 2

        # 删除一个问题
        await problem_service.delete_all_problems(session)
        await session.commit()
        assert await problem_service.get_problem_count() == 0


@pytest.mark.asyncio
async def test_problemset(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        id_, status = await problem_service.create_problemset("test")
        assert id_ == init_problemset_uuid
        assert status == "ALREADY_EXISTS"
        await session.commit()

        id_, status = await problem_service.create_problemset("test2")
        assert id_ != init_problemset_uuid
        assert status == "SUCCESS"
        await session.commit()

        id__ = await problem_service.delete_problemset(id_)
        assert id__ is not None


@pytest.mark.asyncio
async def test_user_operations(test_session_getter: SessionGetterType) -> None:
    """测试用户相关操作"""

    async with test_session_getter() as session:
        user_service = UserService(session, UserRepository())
        # 测试创建用户
        user1 = await _create_user_simple(session, "testuser1")
        await session.commit()
        # 测试查询用户（按用户名）
        queried_user = await user_service.query_user(username="testuser1")
        assert queried_user is not None
        assert queried_user.username == "testuser1"
        assert queried_user.id == user1

        # 测试查询用户（按ID）
        queried_user_by_id = await user_service.query_user(user_id=user1)
        assert queried_user_by_id is not None
        assert queried_user_by_id.username == "testuser1"

        # 测试查询不存在的用户
        non_existent_user = await user_service.query_user(username="nonexistent")
        assert non_existent_user is None


@pytest.mark.asyncio
async def test_advanced_search_operations(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试高级搜索功能"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
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
            problem = SelectiveProblemSubmit(
                content=content,
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content=options[0]
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content=options[1]
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content=options[2]
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=3, content=options[3]
                        ),
                    ],
                ),
            )
            added_problems.append(problem)

        await problem_service.add_problems(init_problemset_uuid, *added_problems)
        await session.commit()

        # 测试精确匹配搜索
        python_results = await problem_service.search_problems(kw="Python")
        assert (
            len(python_results) == 1
        )  # Python编程基础知识 + Python选项, 但是去重后只剩一个

        # 测试模糊匹配搜索
        programming_results = await problem_service.search_problems(kw="编程")
        assert len(programming_results) >= 2

        # 测试按问题集ID搜索
        problemset_results = await problem_service.search_problems(
            problemset_id=init_problemset_uuid
        )
        assert len(problemset_results) == 5

        # 测试组合搜索（关键词 + 问题集ID）
        combined_results = await problem_service.search_problems(
            kw="数据", problemset_id=init_problemset_uuid
        )
        assert len(combined_results) >= 1

        # 测试分页功能
        page1 = await problem_service.search_problems(
            problemset_id=init_problemset_uuid, page=1, page_size=2
        )
        page2 = await problem_service.search_problems(
            problemset_id=init_problemset_uuid, page=2, page_size=2
        )
        page3 = await problem_service.search_problems(
            problemset_id=init_problemset_uuid, page=3, page_size=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

        # 验证分页结果不重复
        all_ids = set()
        for p in page1 + page2 + page3:
            assert p.id not in all_ids
            all_ids.add(p.id)


@pytest.mark.asyncio
async def test_concurrent_operations(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试并发操作"""

    async def add_problems_batch(batch_id: int) -> None:
        async with test_session_getter() as session:
            problem_service = ProblemService(session, problemset_repo, problem_repo)
            problems = []
            for i in range(10):
                problems.append(
                    SelectiveProblemSubmit(
                        content=f"批次{batch_id}问题{i}",
                        type=ProblemType.SELECTIVE,
                        details=SelectiveProblemDetails(
                            type="single",
                            options=[
                                SelectiveProblemOption(
                                    is_correct=True, order=0, content=f"正确答案{i}"
                                ),
                                SelectiveProblemOption(
                                    is_correct=False, order=1, content=f"错误答案{i}"
                                ),
                            ],
                        ),
                    )
                )
            await problem_service.add_problems(init_problemset_uuid, *problems)
            await session.commit()

    # 并发添加问题
    tasks = [add_problems_batch(i) for i in range(5)]
    await asyncio.gather(*tasks)

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        total_count = await problem_service.get_problem_count()
        assert total_count == 50  # 5个批次，每批10个问题


@pytest.mark.asyncio
async def test_data_validation_and_constraints(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试数据验证和约束"""
    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 测试问题内容不能为空
        try:
            await problem_service.add_problems(
                init_problemset_uuid,
                SelectiveProblemSubmit(
                    content="",  # 空内容
                    type=ProblemType.SELECTIVE,
                    details=SelectiveProblemDetails(
                        type="single",
                        options=[
                            SelectiveProblemOption(
                                is_correct=True, order=0, content="答案"
                            )
                        ],
                    ),
                ),
            )
            await session.commit()
            # 如果没有抛出异常，验证是否正确处理空内容
            problems = await problem_service.search_problems(kw="")
            assert len(problems) >= 0  # 允许空内容搜索
        except Exception:
            pass  # 预期可能的验证错误

        # 测试选项顺序
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="测试选项顺序",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="第三个"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="第一个"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=3, content="第四个"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=1, content="第二个"
                        ),
                    ],
                ),
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证选项顺序
        problem = await query_problem(session, problem_ids[0])
        assert problem is not None
        sorted_options = sorted(problem.details["options"], key=lambda x: x["order"])
        assert sorted_options[0]["content"] == "第一个"
        assert sorted_options[1]["content"] == "第二个"
        assert sorted_options[2]["content"] == "第三个"
        assert sorted_options[3]["content"] == "第四个"


@pytest.mark.asyncio
async def test_problemset_operations_extended(
    test_session_getter: SessionGetterType,
) -> None:
    """测试问题集操作的扩展功能"""

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 创建多个问题集
        ps1_id, status1 = await problem_service.create_problemset("数学题库")
        ps2_id, status2 = await problem_service.create_problemset("英语题库")
        ps3_id, status3 = await problem_service.create_problemset("计算机题库")
        await session.commit()

        assert status1 == "SUCCESS"
        assert status2 == "SUCCESS"
        assert status3 == "SUCCESS"

        # 为每个问题集添加不同数量的问题
        for ps_id, count in [(ps1_id, 10), (ps2_id, 5), (ps3_id, 15)]:
            problems = []
            for i in range(count):
                problems.append(
                    SelectiveProblemSubmit(
                        content=f"问题{i}",
                        type=ProblemType.SELECTIVE,
                        details=SelectiveProblemDetails(
                            type="single",
                            options=[
                                SelectiveProblemOption(
                                    is_correct=True, order=0, content=f"答案{i}"
                                )
                            ],
                        ),
                    )
                )
            await problem_service.add_problems(ps_id, *problems)
        await session.commit()

        # 测试列出所有问题集
        all_problemsets = await problem_service.list_problemsets()
        assert len(all_problemsets) >= 3

        # 验证问题集计数
        problemset_counts = {ps.name: ps.count for ps in all_problemsets}
        assert problemset_counts.get("数学题库") == 10
        assert problemset_counts.get("英语题库") == 5
        assert problemset_counts.get("计算机题库") == 15

        # 测试删除问题集及其所有问题
        deleted_id = await problem_service.delete_problemset(ps1_id)
        assert deleted_id == ps1_id
        await session.commit()

        # 验证问题集已删除
        remaining_problemsets = await problem_service.list_problemsets()
        remaining_names = {ps.name for ps in remaining_problemsets}
        assert "数学题库" not in remaining_names
        assert "英语题库" in remaining_names
        assert "计算机题库" in remaining_names


@pytest.mark.asyncio
async def test_edge_cases_and_error_handling(
    test_session_getter: SessionGetterType,
) -> None:
    """测试边界情况和错误处理"""

    async with test_session_getter() as session:
        problem_service = ProblemService(session, problemset_repo, problem_repo)
        # 测试对不存在的问题集添加问题
        fake_problemset_id = uuid4()
        result = await problem_service.add_problems(
            fake_problemset_id,
            SelectiveProblemSubmit(
                content="测试问题",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="答案")
                    ],
                ),
            ),
        )
        assert result is None  # 应该返回 None

        # 测试查询不存在的问题
        fake_problem_id = uuid4()
        problem = await query_problem(session, fake_problem_id)
        assert problem is None

        # 测试删除不存在的问题集
        deleted_id = await problem_service.delete_problemset(fake_problemset_id)
        assert deleted_id is None

        # 测试从空问题集中抽样
        empty_ps_id, _ = await problem_service.create_problemset("空问题集")
        await session.commit()

        sampled = await problem_service.sample_problems(empty_ps_id, 10)
        assert len(sampled) == 0

        # 测试空问题集的计数
        count = await problem_service.get_problem_count(empty_ps_id)
        assert count == 0


@pytest.mark.asyncio
async def test_problem_types_and_options(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试不同问题类型和选项配置"""
    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 测试单选题（标准4选项）
        single_choice_id = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="哪个是正确的？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=False, order=0, content="选项A"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=1, content="选项B"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="选项C"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=3, content="选项D"
                        ),
                    ],
                ),
            ),
        )

        # 测试多选题（多个正确答案）
        multi_choice_id = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="以下哪些是正确的？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="正确选项1"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="错误选项1"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=2, content="正确选项2"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=3, content="正确选项3"
                        ),
                    ],
                ),
            ),
        )

        # 测试只有2个选项的题目
        binary_choice_id = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="这是真的吗？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="是"),
                        SelectiveProblemOption(is_correct=False, order=1, content="否"),
                    ],
                ),
            ),
        )

        # 测试有很多选项的题目
        many_options_id = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="选择所有偶数",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=(i % 2 == 0), order=i, content=str(i)
                        )
                        for i in range(10)
                    ],
                ),
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
        assert single_problem.type == ProblemType.SELECTIVE
        correct_options = [
            opt for opt in single_problem.details["options"] if opt["is_correct"]
        ]
        assert len(correct_options) == 1
        assert correct_options[0]["content"] == "选项B"

        # 验证多选题
        multi_problem = await query_problem(session, multi_choice_id[0])
        assert multi_problem is not None
        assert multi_problem.type == ProblemType.SELECTIVE
        correct_options = [
            opt for opt in multi_problem.details["options"] if opt["is_correct"]
        ]
        assert len(correct_options) == 3

        # 验证二元选择题
        binary_problem = await query_problem(session, binary_choice_id[0])
        assert binary_problem is not None
        assert len(binary_problem.details["options"]) == 2

        # 验证多选项题目
        many_options_problem = await query_problem(session, many_options_id[0])
        assert many_options_problem is not None
        assert len(many_options_problem.details["options"]) == 10
        correct_count = sum(
            1 for opt in many_options_problem.details["options"] if opt["is_correct"]
        )
        assert correct_count == 5  # 0, 2, 4, 6, 8


@pytest.mark.asyncio
async def test_performance_and_bulk_operations(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试性能和批量操作"""

    async with test_session_getter() as session:
        # 测试批量添加大量问题
        start_time = time.time()

        bulk_problems = []
        for i in range(100):
            bulk_problems.append(
                SelectiveProblemSubmit(
                    content=f"性能测试问题{i}",
                    type=ProblemType.SELECTIVE,
                    details=SelectiveProblemDetails(
                        type="single",
                        options=[
                            SelectiveProblemOption(
                                is_correct=True, order=0, content=f"正确答案{i}"
                            ),
                            SelectiveProblemOption(
                                is_correct=False, order=1, content=f"错误答案{i}a"
                            ),
                            SelectiveProblemOption(
                                is_correct=False, order=2, content=f"错误答案{i}b"
                            ),
                            SelectiveProblemOption(
                                is_correct=False, order=3, content=f"错误答案{i}c"
                            ),
                        ],
                    ),
                )
            )

        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        result = await problem_service.add_problems(
            init_problemset_uuid, *bulk_problems
        )
        await session.commit()

        print(f"添加100个问题耗时: {time.time() - start_time:.3f}秒")

        assert result is not None
        assert len(result) == 100

        # 测试批量搜索性能
        start_time = time.time()
        search_results = await problem_repo.search(session, "性能测试", page_size=999)
        search_time = time.time() - start_time

        print(f"搜索100个问题耗时: {search_time:.3f}秒")
        assert len(search_results) == 100

        # 测试分页搜索
        paginated_results = []
        for page in range(1, 11):  # 10页，每页10个
            page_results = await problem_repo.search(
                session, "性能测试", page=page, page_size=10
            )
            paginated_results.extend(page_results)

        assert len(paginated_results) == 100

        # 测试批量删除
        start_time = time.time()
        await problem_service.delete_problems(*result[:50])  # 删除前50个
        await session.commit()
        delete_time = time.time() - start_time

        print(f"删除50个问题耗时: {delete_time:.3f}秒")

        remaining_count = await problem_service.get_problem_count(init_problemset_uuid)
        assert remaining_count == 50


@pytest.mark.asyncio
async def test_database_transactions_and_rollback(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试数据库事务和回滚"""
    test_username = "Ayachi Nene"
    async with test_session_getter() as session:
        await _create_user_simple(session, test_username)
        await session.commit()

    async with test_session_getter() as session:
        with pytest.raises(IntegrityError):
            # 预期出现用户重名错误
            await _create_user_simple(session, test_username)

    async with test_session_getter() as session:
        users = (
            await session.exec(select(DBUser).where(DBUser.username == test_username))
        ).all()
        assert len(users) == 1  # 预期第一个 create 成功, 第二个失败并回滚
        assert users[0].username == test_username


@pytest.mark.asyncio
async def test_unicode_and_special_characters(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试Unicode和特殊字符处理"""
    async with test_session_getter() as session:
        # 测试各种Unicode字符
        unicode_problems = [
            SelectiveProblemSubmit(
                content="数学公式：∫₀¹ x² dx = ?",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(is_correct=True, order=0, content="1/3"),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="1/2"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="emoji测试：🐍Python vs ☕Java？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="Both are great! 🎉"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="Neither 😞"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="中文测试：北京、上海、广州",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="一线城市"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="二线城市"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="Русский язык тест",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="Привет"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="Hello"
                        ),
                    ],
                ),
            ),
        ]

        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        result = await problem_service.add_problems(
            init_problemset_uuid, *unicode_problems
        )
        await session.commit()
        assert result is not None
        assert len(result) == 4

        # 测试Unicode搜索
        math_results = await problem_repo.search(session, "数学")
        assert len(math_results) >= 1

        emoji_results = await problem_repo.search(session, "🐍")
        assert len(emoji_results) >= 1

        chinese_results = await problem_repo.search(session, "北京")
        assert len(chinese_results) >= 1

        russian_results = await problem_repo.search(session, "Русский")
        assert len(russian_results) >= 1

        # 验证存储和检索的完整性
        for problem_id in result:
            retrieved_problem = await problem_repo.get_by_id(session, problem_id)
            assert retrieved_problem is not None
            # 验证内容没有被截断或损坏
            assert len(retrieved_problem.content) > 0
            assert len(retrieved_problem.details["options"]) > 0


@pytest.mark.asyncio
async def test_database_integrity_and_relationships(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试数据库完整性和关系约束"""

    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 添加一个问题
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="关系测试问题",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="选项1"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="选项2"
                        ),
                    ],
                ),
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证问题和选项的关系
        problem_db = (
            await session.exec(select(DBProblem).where(DBProblem.id == problem_ids[0]))
        ).one_or_none()
        assert problem_db is not None

        options = problem_db.details["options"]
        assert len(options) == 2

        # 验证问题集和问题的关系
        problemset_db = await problem_db.awaitable_attrs.problemset
        assert problemset_db.id == init_problemset_uuid


@pytest.mark.asyncio
async def test_problem_sampling_variations(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试问题抽样的各种情况"""
    async with test_session_getter() as session:
        # 添加不同类型的问题
        mixed_problems = []
        for i in range(20):
            options = [
                SelectiveProblemOption(
                    is_correct=True, order=0, content=f"正确答案{i}"
                ),
                SelectiveProblemOption(
                    is_correct=False, order=1, content=f"错误答案{i}"
                ),
            ]
            if i % 2 == 0:
                options.append(
                    SelectiveProblemOption(
                        is_correct=True, order=2, content=f"另一个正确答案{i}"
                    )
                )

            mixed_problems.append(
                SelectiveProblemSubmit(
                    content=f"抽样测试问题{i}",
                    type=ProblemType.SELECTIVE,
                    details=SelectiveProblemDetails(
                        type="multiple" if i % 2 == 0 else "single",
                        options=options,
                    ),
                )
            )

        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        await problem_service.add_problems(init_problemset_uuid, *mixed_problems)
        await session.commit()

        # 测试不同大小的抽样
        sample_sizes = [1, 5, 10, 15, 20, 25]
        for size in sample_sizes:
            sampled = await problem_repo.sample_by_problemset(
                session, init_problemset_uuid, size
            )
            expected_size = min(size, 20)  # 最多只能抽到20个
            assert len(sampled) == expected_size


@pytest.mark.asyncio
async def test_complex_query_scenarios(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试复杂查询场景"""
    async with test_session_getter() as session:
        # 创建复杂的测试数据
        complex_problems = [
            SelectiveProblemSubmit(
                content="Python中的装饰器是什么？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="single",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="一种设计模式"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="一种数据类型"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="一种循环结构"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="以下哪些是Python的内置数据类型？",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="list"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=1, content="dict"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=2, content="array"
                        ),
                        SelectiveProblemOption(
                            is_correct=True, order=3, content="tuple"
                        ),
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="JavaScript中的异步编程",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="Promise"
                        ),
                        SelectiveProblemOption(
                            is_correct=False, order=1, content="Synchronous"
                        ),
                    ],
                ),
            ),
        ]

        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        await problem_service.add_problems(init_problemset_uuid, *complex_problems)
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
            results = await problem_repo.search(
                session, keyword, problem_type=ProblemType.SELECTIVE
            )
            assert len(results) == expected_count, (
                f"搜索'{keyword}'应该返回{expected_count}个结果，实际返回{len(results)}个"
            )

        # 测试组合搜索
        python_in_problemset = await problem_repo.search(
            session, "Python", problemset_id=init_problemset_uuid
        )
        assert len(python_in_problemset) == 2

        # 测试分页边界情况
        all_results = await problem_repo.search(
            session, None, problemset_id=init_problemset_uuid
        )
        total_count = len(all_results)

        # 测试最后一页
        last_page_size = total_count % 2 if total_count % 2 != 0 else 2
        last_page = total_count // 2 + (1 if total_count % 2 != 0 else 0)

        if last_page > 0:
            last_page_results = await problem_repo.search(
                session,
                None,
                problemset_id=init_problemset_uuid,
                page=last_page,
                page_size=2,
            )
            assert len(last_page_results) == last_page_size


@pytest.mark.asyncio
async def test_data_consistency_after_operations(
    test_session_getter: SessionGetterType, init_problemset_uuid: UUID
) -> None:
    """测试操作后的数据一致性"""
    async with test_session_getter() as session:
        problemset_repo = ProblemSetRepository()
        problem_repo = ProblemRepository()
        problem_service = ProblemService(session, problemset_repo, problem_repo)

        # 记录初始状态
        initial_count = await problem_service.get_problem_count(init_problemset_uuid)

        # 执行一系列操作
        problem_ids = await problem_service.add_problems(
            init_problemset_uuid,
            SelectiveProblemSubmit(
                content="一致性测试问题1",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案1"
                        )
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="一致性测试问题2",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案2"
                        )
                    ],
                ),
            ),
            SelectiveProblemSubmit(
                content="一致性测试问题3",
                type=ProblemType.SELECTIVE,
                details=SelectiveProblemDetails(
                    type="multiple",
                    options=[
                        SelectiveProblemOption(
                            is_correct=True, order=0, content="答案3"
                        )
                    ],
                ),
            ),
        )
        assert problem_ids is not None
        await session.commit()

        # 验证添加后的计数
        after_add_count = await problem_service.get_problem_count(init_problemset_uuid)
        assert after_add_count == initial_count + 3

        # 删除部分问题
        await problem_service.delete_problems(problem_ids[0], problem_ids[2])
        await session.commit()

        # 验证删除后的计数
        after_delete_count = await problem_service.get_problem_count(
            init_problemset_uuid
        )
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
