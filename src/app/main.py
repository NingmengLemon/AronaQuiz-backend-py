import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


origins: list[str] = ["*"]  # 开发阶段就先这样
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origin_regex=r"https://",
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Custom-Header"],
    max_age=600,
)
