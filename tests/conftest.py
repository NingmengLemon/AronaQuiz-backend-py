import functools
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.config import INMEM_SQLITE_URL
from app.db.utils import get_session, new_engine
from app.main import app
from app.typ import SessionGetterType


@pytest.fixture(scope="module", autouse=True, name="test_engine")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    engine = new_engine(INMEM_SQLITE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="module")
def test_session_getter(test_engine: AsyncEngine) -> SessionGetterType:
    return functools.partial(get_session, engine=test_engine)


@pytest.fixture(scope="module")
async def test_client(test_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""

    async def get_test_session_override() -> AsyncGenerator[AsyncSession]:
        async with get_session(test_engine) as session:
            yield session

    deps.speedlimiter = None
    app.dependency_overrides[deps.get_session_dependency] = get_test_session_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
