import uuid
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import delete, select

from app.api.deps import set_session_getter
from app.db.core import AsyncDatabaseCore
from app.db.models import TABLES, DBAnswerRecord, DBProblemSet, DBUser
from app.db.operations import create_problemset, create_user, delete_all
from app.main import app

# 测试数据库配置
TEST_DB_NAME = "test_apis"


@pytest.fixture(scope="module")
async def test_db() -> AsyncGenerator[AsyncDatabaseCore, None]:
    """创建测试数据库"""
    import os

    if os.path.exists(f := f"data/{TEST_DB_NAME}.db"):
        os.remove(f)

    DATABASE_URL = f"sqlite+aiosqlite:///data/{TEST_DB_NAME}.db"
    db = AsyncDatabaseCore(DATABASE_URL, TABLES)
    await db.startup()

    # 设置session getter
    set_session_getter(db.get_session)

    yield db

    # 清理
    set_session_getter(None)


@pytest.fixture(scope="function")
async def setup_test_data(
    test_db: AsyncDatabaseCore,
) -> AsyncGenerator[tuple[uuid.UUID, uuid.UUID], None]:
    """为每个测试准备数据"""
    async with test_db.get_session() as session:
        # 清理现有数据
        await delete_all(session)
        await session.exec(delete(DBUser))  # type: ignore
        await session.exec(delete(DBAnswerRecord))  # type: ignore

        await session.commit()

        # 创建测试问题集
        problemset_id, status = await create_problemset(session, "测试题库")
        await session.commit()

        # 创建测试用户
        user = await create_user(session, "testuser")
        await session.commit()

        yield problemset_id, user.id


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


class TestProblemAPI:
    """测试问题相关API"""

    async def test_create_problemset(
        self, client: TestClient, test_db: AsyncDatabaseCore
    ) -> None:
        """测试创建问题集"""
        response = client.post("/api/v1/problem/create_set", json={"name": "数学题库"})
        data = response.json()
        assert response.status_code == 200, data
        assert "id" in data
        assert data["status"] == "success"

        # 验证问题集确实创建了
        async with test_db.get_session() as session:
            problemset = (await session.exec(select(DBProblemSet))).first()
            assert problemset is not None
            assert problemset.name == "数学题库"

    async def test_create_duplicate_problemset(self, client: TestClient) -> None:
        """测试创建重复问题集"""
        # 第一次创建
        response1 = client.post("/api/v1/problem/create_set", json={"name": "重复题库"})
        assert response1.status_code == 200

        # 第二次创建相同名称
        response2 = client.post("/api/v1/problem/create_set", json={"name": "重复题库"})
        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "already_exists"

    async def test_list_problemsets(
        self, client: TestClient, test_db: AsyncDatabaseCore
    ) -> None:
        """测试列出问题集"""
        # 先创建几个问题集
        async with test_db.get_session() as session:
            await session.exec(delete(DBProblemSet))  # type: ignore
            await session.commit()

        client.post("/api/v1/problem/create_set", json={"name": "题库1"})
        client.post("/api/v1/problem/create_set", json={"name": "题库2"})

        response = client.get("/api/v1/problem/list_set")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(ps["name"] == "题库1" for ps in data)
        assert any(ps["name"] == "题库2" for ps in data)

    async def test_add_problems(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试添加问题"""
        problemset_id, _ = setup_test_data

        test_problems = [
            {
                "content": "测试问题1",
                "type": "single_select",
                "options": [
                    {"content": "选项A", "order": 0, "is_correct": True},
                    {"content": "选项B", "order": 1, "is_correct": False},
                ],
            },
            {
                "content": "测试问题2",
                "type": "multi_select",
                "options": [
                    {"content": "选项A", "order": 0, "is_correct": True},
                    {"content": "选项B", "order": 1, "is_correct": True},
                    {"content": "选项C", "order": 2, "is_correct": False},
                ],
            },
        ]

        response = client.post(
            "/api/v1/problem/add",
            json={"problems": test_problems, "problemset_id": str(problemset_id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # 返回两个问题的ID

    async def test_add_problems_to_nonexistent_set(self, client: TestClient) -> None:
        """测试向不存在的问题集添加问题"""
        nonexistent_id = "12345678-1234-1234-1234-123456789012"

        response = client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "测试问题",
                        "type": "single_select",
                        "options": [
                            {"content": "选项", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": nonexistent_id,
            },
        )
        assert response.status_code == 404

    async def test_search_problems(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试搜索问题"""
        problemset_id, _ = setup_test_data

        # 先添加一些问题
        add_response = client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "Python编程问题",
                        "type": "single_select",
                        "options": [
                            {"content": "正确答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )
        assert add_response.status_code == 200

        # 搜索问题
        response = client.get("/api/v1/problem/search?kw=Python")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "Python" in data[0]["content"]

    async def test_get_problems(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试获取问题列表"""
        problemset_id, _ = setup_test_data

        # 添加问题
        client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "测试问题",
                        "type": "single_select",
                        "options": [
                            {"content": "答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )

        # 获取问题列表
        response = client.get(f"/api/v1/problem/get?problemset_id={problemset_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "测试问题"

    async def test_get_problem_count(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试获取问题计数"""
        problemset_id, _ = setup_test_data

        # 初始计数应为0
        response = client.get(f"/api/v1/problem/count?problemset_id={problemset_id}")
        assert response.status_code == 200
        assert response.json() == 0

        # 添加问题后计数应为1
        client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "测试问题",
                        "type": "single_select",
                        "options": [
                            {"content": "答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )

        response = client.get(f"/api/v1/problem/count?problemset_id={problemset_id}")
        assert response.status_code == 200
        assert response.json() == 1

    async def test_delete_problems(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试删除问题"""
        problemset_id, _ = setup_test_data

        # 先添加问题
        add_response = client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "要删除的问题",
                        "type": "single_select",
                        "options": [
                            {"content": "答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )
        problem_id = add_response.json()[0]

        # 删除问题
        response = client.post("/api/v1/problem/delete", json=[problem_id])
        assert response.status_code == 200
        assert response.json() == "ok"

        # 验证问题已被删除
        count_response = client.get(
            f"/api/v1/problem/count?problemset_id={problemset_id}"
        )
        assert count_response.json() == 0


class TestSheetAPI:
    """测试答题表相关API"""

    async def test_get_random_problems(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试获取随机问题"""
        problemset_id, _ = setup_test_data

        # 先添加一些问题
        client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "随机问题1",
                        "type": "single_select",
                        "options": [
                            {"content": "答案1", "order": 0, "is_correct": True}
                        ],
                    },
                    {
                        "content": "随机问题2",
                        "type": "single_select",
                        "options": [
                            {"content": "答案2", "order": 0, "is_correct": True}
                        ],
                    },
                ],
                "problemset_id": str(problemset_id),
            },
        )

        # 获取随机问题
        response = client.get(f"/api/v1/sheet/random?problemset_id={problemset_id}&n=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_report_attempt(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试报告答题尝试"""
        problemset_id, user_id = setup_test_data

        # 先添加一个问题
        add_response = client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "答题测试问题",
                        "type": "single_select",
                        "options": [
                            {"content": "答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )
        problem_id = add_response.json()[0]

        # 报告答题尝试（正确）
        response = client.post(
            "/api/v1/sheet/report",
            json={
                "problem_id": str(problem_id),
                "correct": True,
                "user_id": str(user_id),
            },
        )
        assert response.status_code == 200
        assert response.json() == "ok"

        # 报告答题尝试（错误）
        response = client.post(
            "/api/v1/sheet/report",
            json={
                "problem_id": str(problem_id),
                "correct": False,
                "user_id": str(user_id),
            },
        )
        assert response.status_code == 200
        assert response.json() == "ok"

    async def test_report_attempt_nonexistent_problem(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试报告不存在的问题的答题尝试"""
        _, user_id = setup_test_data
        nonexistent_id = "12345678-1234-1234-1234-123456789012"

        response = client.post(
            "/api/v1/sheet/report",
            json={
                "problem_id": str(nonexistent_id),
                "correct": True,
                "user_id": str(user_id),
            },
        )
        assert response.status_code == 404

    async def test_report_attempt_nonexistent_user(
        self, client: TestClient, setup_test_data: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """测试报告不存在的用户的答题尝试"""
        problemset_id, _ = setup_test_data

        # 添加问题
        add_response = client.post(
            "/api/v1/problem/add",
            json={
                "problems": [
                    {
                        "content": "用户测试问题",
                        "type": "single_select",
                        "options": [
                            {"content": "答案", "order": 0, "is_correct": True}
                        ],
                    }
                ],
                "problemset_id": str(problemset_id),
            },
        )
        problem_id = add_response.json()[0]

        nonexistent_user_id = "12345678-1234-1234-1234-123456789012"
        response = client.post(
            "/api/v1/sheet/report",
            json={
                "problem_id": str(problem_id),
                "correct": True,
                "user_id": str(nonexistent_user_id),
            },
        )
        assert response.status_code == 404
