import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import router as api_router
from .api.deps import set_session_getter
from .db.core import AsyncDatabaseCore
from .db.models import TABLES


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    os.makedirs("./data", exist_ok=True)
    DB_NAME = "hdusp2"
    DATABASE_URL = f"sqlite+aiosqlite:///data/{DB_NAME}.db"

    dbcore = AsyncDatabaseCore(DATABASE_URL, TABLES)
    await dbcore.startup()
    set_session_getter(dbcore.get_session)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api")
