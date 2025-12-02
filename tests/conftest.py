import functools
import logging
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.config import INMEM_SQLITE_URL
from app.main import app
from app.models.db.base import arona_metadata
from app.typ import SessionGetterType
from app.utils.db.utils import get_session, new_engine

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True, name="test_engine")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    logger.info("Creating test engine fixture.")
    engine = new_engine(INMEM_SQLITE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(arona_metadata.create_all)
    logger.info("Test engine fixture created.")
    yield engine
    logger.info("Test engine fixture teardown complete.")


@pytest.fixture(scope="module")
def test_session_getter(test_engine: AsyncEngine) -> SessionGetterType:
    logger.info("Creating test session getter fixture.")
    return functools.partial(get_session, engine=test_engine)


@pytest.fixture(scope="module")
async def test_client(test_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    logger.info("Creating test client fixture.")
    """创建测试客户端"""

    async def get_test_session_override() -> AsyncGenerator[AsyncSession]:
        async with get_session(test_engine) as session:
            yield session

    deps.speedlimiter = None
    app.dependency_overrides[deps.get_session_dependency] = get_test_session_override
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        logger.info("Test client fixture created.")
        yield ac
    logger.info("Test client fixture teardown complete.")
    app.dependency_overrides.clear()
