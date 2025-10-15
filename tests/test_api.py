from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlmodel import delete

from app.db.models import TABLES, UserRole
from app.db.operations import create_user
from app.schemas.response import ProblemSetCreateStatus
from app.typ import SessionGetterType


@dataclass
class PreparedTestData:
    cuid: UUID
    auid: UUID
    suid: UUID


PASSWORD_FOR_TEST = "0d000721"
PROBLEMSET_NAME_FOR_TEST = "Generic Problemset"


@pytest.fixture(scope="function")
async def setup_test_data(
    test_session_getter: SessionGetterType,
) -> AsyncGenerator[PreparedTestData, None]:
    """为每个测试准备数据"""
    async with test_session_getter() as session:
        # 清理现有数据
        for table in TABLES:
            await session.exec(delete(table))  # type: ignore
        await session.commit()

        # 创建测试用户
        common_user_id = await create_user(
            session,
            "commonuser",
            email="common@example.com",
            nickname="普通用户",
            password=PASSWORD_FOR_TEST,
            role=UserRole.USER,
        )
        admin_id = await create_user(
            session,
            "admin",
            email="admin@example.com",
            nickname="权限狗",
            password=PASSWORD_FOR_TEST,
            role=UserRole.ADMIN,
        )
        su_id = await create_user(
            session,
            "superuser",
            email="su@example.com",
            nickname="萝莉超管卡瓦",
            password=PASSWORD_FOR_TEST,
            role=UserRole.SU,
        )

    yield PreparedTestData(
        common_user_id,
        admin_id,
        su_id,
    )


@pytest.fixture
async def cu_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    resp = await test_client.post(
        "/api/v1/session/login",
        json={"user_id": str(setup_test_data.cuid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    return {"Authorization": f"Bearer {result['access_token']}"}


@pytest.fixture
async def su_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    resp = await test_client.post(
        "/api/v1/session/login",
        json={"user_id": str(setup_test_data.suid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    return {"Authorization": f"Bearer {result['access_token']}"}


@pytest.fixture
async def admin_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    resp = await test_client.post(
        "/api/v1/session/login",
        json={"user_id": str(setup_test_data.auid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    return {"Authorization": f"Bearer {result['access_token']}"}


@pytest.fixture
async def test_problemset(
    test_client: AsyncClient,
    admin_auth_headers: dict[str, str],
) -> UUID:
    # 虽然有点不正式但是这里隐式包含了创建问题集的测试
    # 所以后面大概就不用写了 (x)
    resp = await test_client.post(
        "/api/v1/problem/create_set",
        headers=admin_auth_headers,
        json={"name": PROBLEMSET_NAME_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    return UUID(result["id"])


class TestProblemAPIs:
    async def test_list_problemset(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
    ) -> None:
        resp = await test_client.get(
            "/api/v1/problem/list_set", headers=cu_auth_headers
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 1
        assert UUID(result[0]["id"]) == test_problemset

    async def test_create_duplicated_problemset(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        admin_auth_headers: dict[str, str],
    ) -> None:
        resp = await test_client.post(
            "/api/v1/problem/create_set",
            headers=admin_auth_headers,
            json={"name": PROBLEMSET_NAME_FOR_TEST},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert (
            ProblemSetCreateStatus(result["status"])
            == ProblemSetCreateStatus.ALREADY_EXISTS
        )
        assert UUID(result["id"]) == test_problemset

    async def test_add_problems(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试添加题目"""
        problem_data = [
            {
                "content": "Python是一种什么类型的语言？",
                "type": "single_select",
                "options": [
                    {"content": "编译型语言", "is_correct": False, "order": 0},
                    {"content": "解释型语言", "is_correct": True, "order": 1},
                    {"content": "汇编语言", "is_correct": False, "order": 2},
                ],
            },
            {
                "content": "以下哪些是Python的数据类型？",
                "type": "multi_select",
                "options": [
                    {"content": "list", "is_correct": True, "order": 0},
                    {"content": "dict", "is_correct": True, "order": 1},
                    {"content": "array", "is_correct": False, "order": 2},
                    {"content": "tuple", "is_correct": True, "order": 3},
                ],
            },
        ]

        resp = await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 2
        assert all(isinstance(UUID(pid), UUID) for pid in result)

    async def test_add_problems_to_nonexistent_set(
        self,
        test_client: AsyncClient,
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试向不存在的问题集添加题目"""
        fake_problemset_id = "12345678-1234-1234-1234-123456789012"
        problem_data = [
            {
                "content": "测试问题",
                "type": "single_select",
                "options": [
                    {"content": "选项A", "is_correct": True, "order": 0},
                ],
            }
        ]

        resp = await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": fake_problemset_id,
                "problems": problem_data,
            },
        )
        assert resp.status_code == 404

    async def test_search_problems(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试搜索题目"""
        # 先添加一些测试题目
        problem_data = [
            {
                "content": "Python编程语言的特点",
                "type": "single_select",
                "options": [
                    {"content": "简单易学", "is_correct": True, "order": 0},
                    {"content": "编译执行", "is_correct": False, "order": 1},
                ],
            },
            {
                "content": "Java是一种编程语言",
                "type": "single_select",
                "options": [
                    {"content": "是的", "is_correct": True, "order": 0},
                    {"content": "不是", "is_correct": False, "order": 1},
                ],
            },
        ]

        await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试搜索包含"Python"的题目
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"kw": "Python"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 1
        assert "Python" in result[0]["content"]

        # 测试搜索包含"编程语言"的题目
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"kw": "编程语言"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 2  # 两个问题都包含"编程语言"

        # 测试按问题集搜索
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"problemset_id": str(test_problemset)},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 2

        # 测试分页搜索
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"page": 1, "page_size": 1},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 1

    async def test_get_problems(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试获取题目（无关键词搜索）"""
        # 先添加测试题目
        problem_data = [
            {
                "content": "测试题目1",
                "type": "single_select",
                "options": [
                    {"content": "答案1", "is_correct": True, "order": 0},
                ],
            },
            {
                "content": "测试题目2",
                "type": "single_select",
                "options": [
                    {"content": "答案2", "is_correct": True, "order": 0},
                ],
            },
        ]

        await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试获取所有题目
        resp = await test_client.get(
            "/api/v1/problem/get",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) >= 2

        # 测试按问题集获取题目
        resp = await test_client.get(
            "/api/v1/problem/get",
            headers=cu_auth_headers,
            params={"problemset_id": str(test_problemset)},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 2

    async def test_get_problem_count(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试获取题目数量"""
        # 先添加测试题目
        problem_data = [
            {
                "content": "计数测试题目1",
                "type": "single_select",
                "options": [
                    {"content": "答案1", "is_correct": True, "order": 0},
                ],
            },
            {
                "content": "计数测试题目2",
                "type": "single_select",
                "options": [
                    {"content": "答案2", "is_correct": True, "order": 0},
                ],
            },
        ]

        await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试获取总题目数
        resp = await test_client.get(
            "/api/v1/problem/count",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result >= 2

        # 测试获取特定问题集的题目数
        resp = await test_client.get(
            "/api/v1/problem/count",
            headers=cu_auth_headers,
            params={"problemset_id": str(test_problemset)},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result == 2

    async def test_random_sample_problems(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
    ) -> None:
        """测试随机抽样题目"""
        # 先添加多个测试题目
        problem_data = []
        for i in range(10):
            problem_data.append(
                {
                    "content": f"抽样测试题目{i}",
                    "type": "single_select",
                    "options": [
                        {"content": f"答案{i}", "is_correct": True, "order": 0},
                    ],
                }
            )

        await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试抽样5个题目
        resp = await test_client.get(
            "/api/v1/problem/random",
            headers=cu_auth_headers,
            params={
                "problemset_id": str(test_problemset),
                "n": 5,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result) == 5

        # 验证抽样结果的结构
        for problem in result:
            assert "content" in problem
            assert "type" in problem
            assert "options" in problem
            assert len(problem["options"]) > 0

    async def test_delete_problems(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试删除题目"""
        # 先添加测试题目
        problem_data = [
            {
                "content": "待删除题目1",
                "type": "single_select",
                "options": [
                    {"content": "答案1", "is_correct": True, "order": 0},
                ],
            },
            {
                "content": "待删除题目2",
                "type": "single_select",
                "options": [
                    {"content": "答案2", "is_correct": True, "order": 0},
                ],
            },
        ]

        resp = await test_client.post(
            "/api/v1/problem/add",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        problem_ids = resp.json()
        assert resp.status_code == 200

        # 验证题目存在
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"kw": "待删除"},
        )
        result = resp.json()
        assert len(result) == 2

        # 删除第一个题目
        resp = await test_client.post(
            "/api/v1/problem/delete",
            headers=admin_auth_headers,
            json=[problem_ids[0]],
        )
        assert resp.status_code == 200
        assert resp.json() == "ok"

        # 验证题目已被删除
        resp = await test_client.get(
            "/api/v1/problem/search",
            headers=cu_auth_headers,
            params={"kw": "待删除"},
        )
        result = resp.json()
        assert len(result) == 1
        assert "待删除题目2" in result[0]["content"]

    async def test_add_problems_permission_denied(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试普通用户无权限添加题目"""
        problem_data = [
            {
                "content": "权限测试题目",
                "type": "single_select",
                "options": [
                    {"content": "答案", "is_correct": True, "order": 0},
                ],
            }
        ]

        resp = await test_client.post(
            "/api/v1/problem/add",
            headers=cu_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        assert resp.status_code == 403

    async def test_delete_problems_permission_denied(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试普通用户无权限删除题目"""
        fake_problem_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.post(
            "/api/v1/problem/delete",
            headers=cu_auth_headers,
            json=[fake_problem_id],
        )
        assert resp.status_code == 403


class TestUserAPIs:
    """用户API测试"""

    async def test_user_register(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试用户注册"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "nickname": "新用户",
            "password": "securepassword123",
        }

        resp = await test_client.post(
            "/api/v1/user/register",
            json=user_data,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "user_id" in result
        assert isinstance(UUID(result["user_id"]), UUID)

    async def test_user_register_duplicate_username(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试重复用户名注册"""
        user_data = {
            "username": "commonuser",  # 已存在的用户名
            "email": "different@example.com",
            "nickname": "不同昵称",
            "password": "password123",
        }

        resp = await test_client.post(
            "/api/v1/user/register",
            json=user_data,
        )
        assert resp.status_code == 400

    async def test_user_register_duplicate_email(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试重复邮箱注册"""
        user_data = {
            "username": "differentuser",
            "email": "common@example.com",  # 已存在的邮箱
            "nickname": "不同昵称",
            "password": "password123",
        }

        resp = await test_client.post(
            "/api/v1/user/register",
            json=user_data,
        )
        assert resp.status_code == 400

    async def test_user_register_duplicate_nickname(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试重复昵称注册"""
        user_data = {
            "username": "differentuser",
            "email": "different@example.com",
            "nickname": "普通用户",  # 已存在的昵称
            "password": "password123",
        }

        resp = await test_client.post(
            "/api/v1/user/register",
            json=user_data,
        )
        assert resp.status_code == 400

    async def test_check_field_availability(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试检查字段可用性"""
        # 测试可用用户名
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "username", "value": "availablename"},
        )
        assert resp.status_code == 200
        assert resp.json() == "ok"

        # 测试可用邮箱
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "email", "value": "available@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json() == "ok"

        # 测试可用昵称
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "nickname", "value": "可用昵称"},
        )
        assert resp.status_code == 200
        assert resp.json() == "ok"

    async def test_check_field_conflict(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试检查字段冲突"""
        # 测试冲突的用户名
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "username", "value": "commonuser"},
        )
        assert resp.status_code == 200
        assert resp.json() == "conflict"

        # 测试冲突的邮箱
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "email", "value": "common@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json() == "conflict"

        # 测试冲突的昵称
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "nickname", "value": "普通用户"},
        )
        assert resp.status_code == 200
        assert resp.json() == "conflict"

    async def test_check_field_invalid(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试检查无效字段"""
        # 测试无效邮箱格式
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "email", "value": "invalid-email"},
        )
        assert resp.status_code == 200
        assert resp.json() == "invalid"

        # 测试无效用户名格式
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "username", "value": "ab"},  # 太短
        )
        assert resp.status_code == 200
        assert resp.json() == "invalid"

        # 测试无效昵称格式
        resp = await test_client.get(
            "/api/v1/user/check_field",
            params={"field": "nickname", "value": "a"},  # 太短
        )
        assert resp.status_code == 200
        assert resp.json() == "invalid"

    async def test_get_my_info(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试获取当前用户信息"""
        resp = await test_client.get(
            "/api/v1/user/me",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "username" in result
        assert "email" in result
        assert "nickname" in result
        assert result["username"] == "commonuser"
        assert result["email"] == "common@example.com"
        assert result["nickname"] == "普通用户"

    async def test_get_user_info(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试获取其他用户信息"""
        resp = await test_client.get(
            "/api/v1/user/info",
            headers=cu_auth_headers,
            params={"user_id": str(setup_test_data.auid)},  # 管理员用户
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "username" in result
        assert "email" in result
        assert "nickname" in result
        assert result["username"] == "admin"
        assert result["email"] == "admin@example.com"
        assert result["nickname"] == "权限狗"


class TestSessionAPIs:
    """会话API测试"""

    async def test_login_by_user_id(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过用户ID登录"""
        resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result
        assert "refresh_token" in result
        assert isinstance(UUID(result["access_token"]), UUID)
        assert isinstance(UUID(result["refresh_token"]), UUID)

    async def test_login_by_username(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过用户名登录"""
        resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "username": "commonuser",
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_login_by_email(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过邮箱登录"""
        resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "email": "common@example.com",
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_login_with_wrong_password(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试使用错误密码登录"""
        resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    async def test_login_with_nonexistent_user(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试使用不存在的用户登录"""
        resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "user_id": "12345678-1234-1234-1234-123456789012",
                "password": "anypassword",
            },
        )
        assert resp.status_code == 401

    async def test_logout(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试登出"""
        resp = await test_client.post(
            "/api/v1/session/logout",
            headers=cu_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == "ok"

    async def test_refresh_token(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试刷新访问令牌"""
        # 先登录获取refresh_token
        login_resp = await test_client.post(
            "/api/v1/session/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": PASSWORD_FOR_TEST,
            },
        )
        login_result = login_resp.json()
        assert login_resp.status_code == 200, login_result
        refresh_token = login_result["refresh_token"]
        access_token = login_result["access_token"]

        # 使用refresh_token刷新
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await test_client.post(
            "/api/v1/session/refresh",
            headers=headers,
            json={"refresh_token": refresh_token},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result
        assert "refresh_token" in result

    async def test_refresh_token_with_invalid_token(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试使用无效的refresh_token"""

        resp = await test_client.post(
            "/api/v1/session/refresh",
            headers=cu_auth_headers,
            json={"refresh_token": str(uuid4())},
        )
        assert resp.status_code == 401, resp.json()

    async def test_access_protected_endpoint_without_auth(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试未认证访问受保护端点"""
        resp = await test_client.get("/api/v1/user/me")
        assert resp.status_code == 401, resp.json()

    async def test_access_protected_endpoint_with_invalid_token(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试使用无效令牌访问受保护端点"""
        headers = {"Authorization": "Bearer invalid-token"}
        resp = await test_client.get("/api/v1/user/me", headers=headers)
        assert resp.status_code == 401, resp.json()
