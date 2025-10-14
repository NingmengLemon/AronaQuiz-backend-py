from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

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
