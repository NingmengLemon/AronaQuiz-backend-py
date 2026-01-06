import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.db.user import UserRole
from app.models.dto.code import BusinessCode
from app.repos import UserRepository
from app.services import UserService
from app.typ import SessionGetterType

logger = logging.getLogger(__name__)


@dataclass
class PreparedTestData:
    cuid: UUID
    auid: UUID
    suid: UUID


PASSWORD_FOR_TEST = "0d000721"
PROBLEMSET_NAME_FOR_TEST = "Generic Problemset"


@pytest_asyncio.fixture(scope="function")
async def setup_test_data(
    test_session_getter: SessionGetterType, test_engine: AsyncEngine
) -> PreparedTestData:
    logger.info("Setting up test data fixture.")
    async with test_session_getter() as session:
        user_service = UserService(session, UserRepository())
        # 创建测试用户
        common_user = await user_service.create_user(
            username="commonuser",
            email="common@example.com",
            nickname="普通用户",
            password=PASSWORD_FOR_TEST,
            role=UserRole.USER,
        )
        admin = await user_service.create_user(
            username="admin",
            email="admin@example.com",
            nickname="权限狗",
            password=PASSWORD_FOR_TEST,
            role=UserRole.ADMIN,
        )
        su = await user_service.create_user(
            username="superuser",
            email="su@example.com",
            nickname="卡瓦萝莉超管",
            password=PASSWORD_FOR_TEST,
            role=UserRole.SU,
        )
        await session.commit()

    logger.info("Test data fixture setup complete.")
    return PreparedTestData(
        common_user.id,
        admin.id,
        su.id,
    )


@pytest_asyncio.fixture(scope="function")
async def cu_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    logger.info("Setting up common user auth headers fixture.")
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"user_id": str(setup_test_data.cuid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    assert result["success"] is True
    assert "data" in result
    assert "access_token" in result["data"]
    logger.info("Common user auth headers fixture setup complete.")
    return {"Authorization": f"Bearer {result['data']['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def su_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    logger.info("Setting up superuser auth headers fixture.")
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"user_id": str(setup_test_data.suid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    assert result["success"] is True
    assert "data" in result
    assert "access_token" in result["data"]
    logger.info("Superuser auth headers fixture setup complete.")
    return {"Authorization": f"Bearer {result['data']['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def admin_auth_headers(
    setup_test_data: PreparedTestData, test_client: AsyncClient
) -> dict[str, str]:
    logger.info("Setting up admin auth headers fixture.")
    resp = await test_client.post(
        "/api/v1/auth/login",
        json={"user_id": str(setup_test_data.auid), "password": PASSWORD_FOR_TEST},
    )
    result = resp.json()
    assert resp.status_code == 200, result
    assert result["success"] is True
    assert "data" in result
    assert "access_token" in result["data"]
    logger.info("Admin auth headers fixture setup complete.")
    return {"Authorization": f"Bearer {result['data']['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def test_problemset(
    test_client: AsyncClient,
    admin_auth_headers: dict[str, str],
) -> UUID:
    logger.info("Setting up test problem set fixture.")
    # 虽然有点不正式但是这里隐式包含了创建问题集的测试
    # 所以后面大概就不用写了 (x)
    resp = await test_client.post(
        "/api/v1/problemsets",
        headers=admin_auth_headers,
        json={
            "name": PROBLEMSET_NAME_FOR_TEST,
            "description": "通用题目集用于测试",
            "is_public": True,
            "tags": ["测试", "通用"],
        },
    )
    result = resp.json()
    assert resp.status_code == 201, result
    assert result["success"] is True
    assert "data" in result
    logger.info("Test problem set fixture setup complete.")
    return UUID(result["data"]["id"])


class TestProblemAPIs:
    @pytest.mark.asyncio
    async def test_search_problemsets(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试搜索题目集"""
        # 先创建多个测试题目集
        problemset_names = ["Python题库", "Java题库", "前端题库", "算法题库"]
        for name in problemset_names:
            resp = await test_client.post(
                "/api/v1/problemsets",
                headers=admin_auth_headers,
                json={
                    "name": name,
                    "description": f"{name}的描述",
                    "is_public": True,
                    "tags": [name.replace("题库", ""), "题库"],
                },
            )
            assert resp.status_code == 201

        # 测试搜索包含"题库"的题目集
        resp = await test_client.get(
            "/api/v1/problemsets",
            headers=cu_auth_headers,
            params={"keyword": "题库"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) >= 4  # 包含测试题目集

        # 测试搜索包含"Python"的题目集
        resp = await test_client.get(
            "/api/v1/problemsets",
            headers=cu_auth_headers,
            params={"keyword": "Python"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]) >= 1
        assert any("Python" in ps["name"] for ps in result["data"])

        # 测试分页搜索
        resp = await test_client.get(
            "/api/v1/problemsets",
            headers=cu_auth_headers,
            params={"page": 1, "page_size": 2},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_problemset_count(
        self,
        test_client: AsyncClient,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试获取题目集数量"""
        # 创建测试题目集
        test_names = ["测试题库1", "测试题库2", "测试题库3"]
        for name in test_names:
            resp = await test_client.post(
                "/api/v1/problemsets",
                headers=admin_auth_headers,
                json={
                    "name": name,
                    "description": f"{name}的描述",
                    "is_public": False,
                    "tags": ["测试", "题库"],
                },
            )
            assert resp.status_code == 201

        # 测试获取总题目集数
        resp = await test_client.get(
            "/api/v1/problemsets/count",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert result["data"] >= 3

        # 测试搜索特定关键词的题目集数量
        resp = await test_client.get(
            "/api/v1/problemsets/count",
            headers=cu_auth_headers,
            params={"keyword": "测试题库"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["data"] >= 3

        # 测试搜索不存在的关键词
        resp = await test_client.get(
            "/api/v1/problemsets/count",
            headers=cu_auth_headers,
            params={"keyword": "不存在的题库"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["data"] == 0

    @pytest.mark.asyncio
    async def test_search_problemsets_empty_keyword(
        self,
        test_problemset: UUID,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试空关键词搜索题目集"""
        resp = await test_client.get(
            "/api/v1/problemsets",
            headers=cu_auth_headers,
            params={"keyword": ""},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) >= 1  # 至少包含测试题目集

    @pytest.mark.asyncio
    async def test_create_duplicated_problemset(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        admin_auth_headers: dict[str, str],
    ) -> None:
        resp = await test_client.post(
            "/api/v1/problemsets",
            headers=admin_auth_headers,
            json={
                "name": PROBLEMSET_NAME_FOR_TEST,
                "description": "通用题目集用于测试",
                "is_public": True,
                "tags": ["测试", "通用"],
            },
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.PROBLEMSET_ALREADY_EXISTS
        assert UUID(result["data"]["id"]) == test_problemset

    @pytest.mark.asyncio
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
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "编译型语言", "is_correct": False, "order": 0},
                        {"content": "解释型语言", "is_correct": True, "order": 1},
                        {"content": "汇编语言", "is_correct": False, "order": 2},
                    ],
                },
            },
            {
                "content": "以下哪些是Python的数据类型？",
                "type": "SELECTIVE",
                "details": {
                    "type": "multiple",
                    "options": [
                        {"content": "list", "is_correct": True, "order": 0},
                        {"content": "dict", "is_correct": True, "order": 1},
                        {"content": "array", "is_correct": False, "order": 2},
                        {"content": "tuple", "is_correct": True, "order": 3},
                    ],
                },
            },
        ]

        resp = await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        result = resp.json()
        assert resp.status_code == 201, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 2
        assert all(isinstance(UUID(pid), UUID) for pid in result["data"])

    @pytest.mark.asyncio
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
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "选项A", "is_correct": True, "order": 0},
                    ],
                },
            }
        ]

        resp = await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": fake_problemset_id,
                "problems": problem_data,
            },
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.PROBLEMSET_NOT_FOUND

    @pytest.mark.asyncio
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
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "简单易学", "is_correct": True, "order": 0},
                        {"content": "编译执行", "is_correct": False, "order": 1},
                    ],
                },
            },
            {
                "content": "Java是一种编程语言",
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "是的", "is_correct": True, "order": 0},
                        {"content": "不是", "is_correct": False, "order": 1},
                    ],
                },
            },
        ]

        await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试搜索包含"Python"的题目
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"keyword": "Python"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 1
        assert "Python" in result["data"][0]["content"]

        # 测试搜索包含"编程语言"的题目
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"keyword": "编程语言"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 2  # 两个问题都包含"编程语言"

        # 测试按问题集搜索
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"problemset_id": str(test_problemset)},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 2

        # 测试分页搜索
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"page": 1, "page_size": 1},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 1

    @pytest.mark.asyncio
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
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "答案1", "is_correct": True, "order": 0},
                    ],
                },
            },
            {
                "content": "计数测试题目2",
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "答案2", "is_correct": True, "order": 0},
                    ],
                },
            },
        ]

        await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试获取总题目数
        resp = await test_client.get(
            "/api/v1/problems/count",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert result["data"] >= 2

        # 测试获取特定问题集的题目数
        resp = await test_client.get(
            "/api/v1/problems/count",
            headers=cu_auth_headers,
            params={"problemset_id": str(test_problemset)},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert result["data"] == 2

    @pytest.mark.asyncio
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
                    "type": "SELECTIVE",
                    "details": {
                        "type": "single",
                        "options": [
                            {"content": f"答案{i}", "is_correct": True, "order": 0},
                        ],
                    },
                }
            )

        await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )

        # 测试抽样5个题目
        resp = await test_client.get(
            "/api/v1/problems/random",
            headers=cu_auth_headers,
            params={
                "problemset_id": str(test_problemset),
                "n": 5,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) == 5

        # 验证抽样结果的结构
        for problem in result["data"]:
            assert "content" in problem
            assert "type" in problem
            assert len(problem["details"]["options"]) > 0

    @pytest.mark.asyncio
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
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "答案1", "is_correct": True, "order": 0},
                    ],
                },
            },
            {
                "content": "待删除题目2",
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "答案2", "is_correct": True, "order": 0},
                    ],
                },
            },
        ]

        resp = await test_client.post(
            "/api/v1/problems",
            headers=admin_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        result = resp.json()
        problem_ids = result["data"]
        assert resp.status_code == 201
        assert result["success"] is True

        # 验证题目存在
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"keyword": "待删除"},
        )
        result = resp.json()
        assert len(result["data"]) == 2

        # 删除第一个题目
        resp = await test_client.request(
            "DELETE",
            "/api/v1/problems",
            headers=admin_auth_headers,
            json=[str(problem_ids[0])],
        )
        assert resp.status_code == 204

        # 验证题目已被删除
        resp = await test_client.get(
            "/api/v1/problems",
            headers=cu_auth_headers,
            params={"keyword": "待删除"},
        )
        result = resp.json()
        assert len(result["data"]) == 1
        assert "待删除题目2" in result["data"][0]["content"]

    @pytest.mark.asyncio
    async def test_add_problems_permission_denied(
        self,
        test_client: AsyncClient,
        test_problemset: UUID,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试普通用户无权限添加题目"""
        problem_data = [
            {
                "content": "权限测试",
                "type": "SELECTIVE",
                "details": {
                    "type": "single",
                    "options": [
                        {"content": "答案1", "is_correct": False, "order": 0},
                        {"content": "答案2", "is_correct": True, "order": 1},
                    ],
                },
            }
        ]

        resp = await test_client.post(
            "/api/v1/problems",
            headers=cu_auth_headers,
            json={
                "problemset_id": str(test_problemset),
                "problems": problem_data,
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_problems_permission_denied(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试普通用户无权限删除题目"""
        fake_problem_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.request(
            "DELETE",
            "/api/v1/problems",
            headers=cu_auth_headers,
            json=[fake_problem_id],
        )
        assert resp.status_code == 403


class TestUserAPIs:
    """用户API测试"""

    @pytest.mark.asyncio
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
            "/api/v1/users",
            json=user_data,
        )
        result = resp.json()
        assert resp.status_code == 201, result
        assert result["success"] is True
        assert "data" in result
        assert "id" in result["data"]
        assert isinstance(UUID(result["data"]["id"]), UUID)

    @pytest.mark.asyncio
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
            "/api/v1/users",
            json=user_data,
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.USERNAME_ALREADY_EXISTS

    @pytest.mark.asyncio
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
            "/api/v1/users",
            json=user_data,
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.EMAIL_ALREADY_EXISTS

    @pytest.mark.asyncio
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
            "/api/v1/users",
            json=user_data,
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NICKNAME_ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_check_field_availability(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试检查字段可用性"""
        # 测试可用用户名
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "username", "value": "availablename"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "ok"

        # 测试可用邮箱
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "email", "value": "available@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "ok"

        # 测试可用昵称
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "nickname", "value": "可用昵称"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "ok"

    @pytest.mark.asyncio
    async def test_check_field_conflict(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试检查字段冲突"""
        # 测试冲突的用户名
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "username", "value": "commonuser"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "conflict"

        # 测试冲突的邮箱
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "email", "value": "common@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "conflict"

        # 测试冲突的昵称
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "nickname", "value": "普通用户"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "conflict"

    @pytest.mark.asyncio
    async def test_check_field_invalid(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试检查无效字段"""
        # 测试无效邮箱格式
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "email", "value": "invalid-email"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "invalid"

        # 测试无效用户名格式
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "username", "value": "ab"},  # 太短
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "invalid"

        # 测试无效昵称格式
        resp = await test_client.get(
            "/api/v1/users/check-availability",
            params={"field": "nickname", "value": "a"},  # 太短
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "invalid"

    @pytest.mark.asyncio
    async def test_get_my_info(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试获取当前用户信息"""
        resp = await test_client.get(
            "/api/v1/users/me",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert "username" in result["data"]
        assert "email" in result["data"]
        assert "nickname" in result["data"]
        assert result["data"]["username"] == "commonuser"
        assert result["data"]["email"] == "common@example.com"
        assert result["data"]["nickname"] == "普通用户"

    @pytest.mark.asyncio
    async def test_get_user_info(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试获取其他用户信息"""
        resp = await test_client.get(
            f"/api/v1/users/{setup_test_data.auid}",  # 管理员用户
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert "username" in result["data"]
        assert "email" in result["data"]
        assert "nickname" in result["data"]
        assert result["data"]["username"] == "admin"
        assert result["data"]["email"] == "admin@example.com"
        assert result["data"]["nickname"] == "权限狗"


class TestSessionAPIs:
    """会话API测试"""

    @pytest.mark.asyncio
    async def test_login_by_user_id(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过用户ID登录"""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result["data"]
        assert "refresh_token" in result["data"]
        assert isinstance(UUID(result["data"]["access_token"]), UUID)
        assert isinstance(UUID(result["data"]["refresh_token"]), UUID)

    @pytest.mark.asyncio
    async def test_login_by_username(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过用户名登录"""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "username": "commonuser",
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result["data"]
        assert "refresh_token" in result["data"]

    @pytest.mark.asyncio
    async def test_login_by_email(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试通过邮箱登录"""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "common@example.com",
                "password": PASSWORD_FOR_TEST,
            },
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result["data"]
        assert "refresh_token" in result["data"]

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试使用错误密码登录"""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": "wrongpassword",
            },
        )
        result = resp.json()
        assert resp.status_code == 401, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.LOGIN_FAILED

    @pytest.mark.asyncio
    async def test_login_with_nonexistent_user(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试使用不存在的用户登录"""
        resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "user_id": "12345678-1234-1234-1234-123456789012",
                "password": "anypassword",
            },
        )
        result = resp.json()
        assert resp.status_code == 401, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.LOGIN_FAILED

    @pytest.mark.asyncio
    async def test_logout(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试登出"""
        resp = await test_client.post(
            "/api/v1/auth/logout",
            headers=cu_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"] == "ok"

    @pytest.mark.asyncio
    async def test_refresh_token(
        self,
        test_client: AsyncClient,
        setup_test_data: PreparedTestData,
    ) -> None:
        """测试刷新访问令牌 - 验证令牌轮换"""
        # 先登录获取refresh_token
        login_resp = await test_client.post(
            "/api/v1/auth/login",
            json={
                "user_id": str(setup_test_data.cuid),
                "password": PASSWORD_FOR_TEST,
            },
        )
        login_result = login_resp.json()
        assert login_resp.status_code == 200, login_result
        old_refresh_token = login_result["data"]["refresh_token"]
        old_access_token = login_result["data"]["access_token"]

        # 使用refresh_token刷新
        headers = {"Authorization": f"Bearer {old_access_token}"}
        resp = await test_client.post(
            "/api/v1/auth/refresh",
            headers=headers,
            json={"refresh_token": old_refresh_token},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert "access_token" in result["data"]
        assert "refresh_token" in result["data"]

        # 验证令牌已轮换
        new_access_token = result["data"]["access_token"]
        new_refresh_token = result["data"]["refresh_token"]
        assert new_access_token != old_access_token
        assert new_refresh_token != old_refresh_token

        # 验证旧令牌已失效
        resp = await test_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {new_access_token}"},
            json={"refresh_token": old_refresh_token},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_with_invalid_token(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试使用无效的refresh_token"""

        resp = await test_client.post(
            "/api/v1/auth/refresh",
            headers=cu_auth_headers,
            json={"refresh_token": str(uuid4())},
        )
        result = resp.json()
        assert resp.status_code == 401, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.TOKEN_REFRESH_FAILED

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_auth(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试未认证访问受保护端点"""
        resp = await test_client.get("/api/v1/users/me")
        assert resp.status_code == 401, resp.json()

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_invalid_token(
        self,
        test_client: AsyncClient,
    ) -> None:
        """测试使用无效令牌访问受保护端点"""
        headers = {"Authorization": "Bearer invalid-token"}
        resp = await test_client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401, resp.json()


class TestTagAPIs:
    """标签API测试"""

    @pytest.mark.asyncio
    async def test_list_tags(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
        test_problemset: UUID,
    ) -> None:
        """测试获取标签列表"""
        # 先通过创建问题集来创建一些标签
        resp = await test_client.post(
            "/api/v1/problemsets",
            headers=admin_auth_headers,
            json={
                "name": "标签测试题目集",
                "description": "用于测试标签的题目集",
                "is_public": True,
                "tags": ["Python", "编程", "测试"],
            },
        )
        assert resp.status_code == 201

        # 测试获取所有标签
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert "tags" in result["data"]
        assert "total" in result["data"]
        assert "page" in result["data"]
        assert "page_size" in result["data"]
        assert len(result["data"]["tags"]) >= 3  # 至少包含Python, 编程, 测试

        # 测试关键词搜索
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
            params={"keyword": "Python"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert len(result["data"]["tags"]) >= 1
        assert any(tag["name"] == "Python" for tag in result["data"]["tags"])

        # 测试分页
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
            params={"page": 1, "page_size": 2},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]["tags"]) == 2

    @pytest.mark.asyncio
    async def test_get_tag_detail(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
        test_problemset: UUID,
    ) -> None:
        """测试获取标签详情"""
        # 先获取一个标签
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
            params={"keyword": "测试"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]["tags"]) >= 1
        tag_id = result["data"]["tags"][0]["id"]

        # 测试获取标签详情
        resp = await test_client.get(
            f"/api/v1/tags/{tag_id}",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["id"] == tag_id
        assert "name" in result["data"]
        assert "problem_count" in result["data"]
        assert "problemset_count" in result["data"]

        # 测试获取不存在的标签
        fake_tag_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.get(
            f"/api/v1/tags/{fake_tag_id}",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_tag(
        self,
        test_client: AsyncClient,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试创建标签（需要管理员权限）"""
        # 测试普通用户无权限创建标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=cu_auth_headers,
            json={"name": "新标签"},
        )
        assert resp.status_code == 403

        # 测试管理员创建标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "新标签"},
        )
        result = resp.json()
        assert resp.status_code == 201, result
        assert result["success"] is True
        assert "data" in result
        assert "id" in result["data"]
        assert result["data"]["name"] == "新标签"
        assert result["data"]["message"] == "标签创建成功"

        # 测试创建重复标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "新标签"},
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.CONFLICT

        # 测试创建无效标签名称
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "无效标签名称@#$"},
        )
        result = resp.json()
        assert resp.status_code == 400, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_update_tag(
        self,
        test_client: AsyncClient,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试更新标签（需要管理员权限）"""
        # 先创建一个标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "待更新标签"},
        )
        result = resp.json()
        assert resp.status_code == 201, result
        tag_id = result["data"]["id"]

        # 测试普通用户无权限更新标签
        resp = await test_client.put(
            f"/api/v1/tags/{tag_id}",
            headers=cu_auth_headers,
            json={"name": "更新后的标签"},
        )
        assert resp.status_code == 403

        # 测试管理员更新标签
        resp = await test_client.put(
            f"/api/v1/tags/{tag_id}",
            headers=admin_auth_headers,
            json={"name": "更新后的标签"},
        )
        result = resp.json()
        print(f"DEBUG: Update response: {result}")  # 添加调试输出
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert result["data"]["id"] == tag_id
        print(
            f"DEBUG: old_name = {result['data'].get('old_name')}, expected = '待更新标签'"
        )
        print(
            f"DEBUG: new_name = {result['data'].get('new_name')}, expected = '更新后的标签'"
        )
        assert result["data"]["old_name"] == "待更新标签"
        assert result["data"]["new_name"] == "更新后的标签"
        assert result["data"]["message"] == "标签更新成功"

        # 测试更新不存在的标签
        fake_tag_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.put(
            f"/api/v1/tags/{fake_tag_id}",
            headers=admin_auth_headers,
            json={"name": "新名称"},
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NOT_FOUND

        # 测试更新为已存在的标签名称
        # 先创建另一个标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "另一个标签"},
        )
        assert resp.status_code == 201

        # 尝试将第一个标签更新为相同名称
        resp = await test_client.put(
            f"/api/v1/tags/{tag_id}",
            headers=admin_auth_headers,
            json={"name": "另一个标签"},
        )
        result = resp.json()
        assert resp.status_code == 409, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.CONFLICT

    @pytest.mark.asyncio
    async def test_delete_tag(
        self,
        test_client: AsyncClient,
        admin_auth_headers: dict[str, str],
        cu_auth_headers: dict[str, str],
    ) -> None:
        """测试删除标签（需要管理员权限）"""
        # 先创建一个标签
        resp = await test_client.post(
            "/api/v1/tags",
            headers=admin_auth_headers,
            json={"name": "待删除标签"},
        )
        result = resp.json()
        assert resp.status_code == 201, result
        tag_id = result["data"]["id"]

        # 测试普通用户无权限删除标签
        resp = await test_client.delete(
            f"/api/v1/tags/{tag_id}",
            headers=cu_auth_headers,
        )
        assert resp.status_code == 403

        # 测试管理员删除标签
        resp = await test_client.delete(
            f"/api/v1/tags/{tag_id}",
            headers=admin_auth_headers,
        )
        assert resp.status_code == 204

        # 验证标签已被删除
        resp = await test_client.get(
            f"/api/v1/tags/{tag_id}",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NOT_FOUND

        # 测试删除不存在的标签
        fake_tag_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.delete(
            f"/api/v1/tags/{fake_tag_id}",
            headers=admin_auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_tag_problems(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
        test_problemset: UUID,
    ) -> None:
        """测试获取标签关联的题目"""
        # 先获取一个标签
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
            params={"keyword": "测试"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]["tags"]) >= 1
        tag_id = result["data"]["tags"][0]["id"]

        # 测试获取标签关联的题目
        resp = await test_client.get(
            f"/api/v1/tags/{tag_id}/problems",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert "tag" in result["data"]
        assert "problems" in result["data"]
        assert "total" in result["data"]
        assert result["data"]["tag"]["id"] == tag_id

        # 验证响应结构
        if result["data"]["problems"]:
            problem = result["data"]["problems"][0]
            assert "id" in problem
            assert "content" in problem
            assert "type" in problem
            assert "problemset_id" in problem

        # 测试获取不存在的标签的题目
        fake_tag_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.get(
            f"/api/v1/tags/{fake_tag_id}/problems",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_tag_problemsets(
        self,
        test_client: AsyncClient,
        cu_auth_headers: dict[str, str],
        admin_auth_headers: dict[str, str],
        test_problemset: UUID,
    ) -> None:
        """测试获取标签关联的题目集"""
        # 先获取一个标签
        resp = await test_client.get(
            "/api/v1/tags",
            headers=cu_auth_headers,
            params={"keyword": "测试"},
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert len(result["data"]["tags"]) >= 1
        tag_id = result["data"]["tags"][0]["id"]

        # 测试获取标签关联的题目集
        resp = await test_client.get(
            f"/api/v1/tags/{tag_id}/problemsets",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 200, result
        assert result["success"] is True
        assert "data" in result
        assert "tag" in result["data"]
        assert "problemsets" in result["data"]
        assert "total" in result["data"]
        assert result["data"]["tag"]["id"] == tag_id

        # 验证响应结构
        if result["data"]["problemsets"]:
            problemset = result["data"]["problemsets"][0]
            assert "id" in problemset
            assert "name" in problemset
            assert "description" in problemset
            assert "is_public" in problemset
            assert "owner_id" in problemset

        # 测试获取不存在的标签的题目集
        fake_tag_id = "12345678-1234-1234-1234-123456789012"
        resp = await test_client.get(
            f"/api/v1/tags/{fake_tag_id}/problemsets",
            headers=cu_auth_headers,
        )
        result = resp.json()
        assert resp.status_code == 404, result
        assert result["success"] is False
        assert result["code"] == BusinessCode.NOT_FOUND
