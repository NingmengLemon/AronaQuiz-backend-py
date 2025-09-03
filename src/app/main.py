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
    DATABASE_URL = f"sqlite+aiosqlite:///data/{DB_NAME}.db"  # 后续要改

    async with AsyncDatabaseCore(DATABASE_URL, TABLES) as dbcore:
        set_session_getter(dbcore.get_session)
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api")


PROD_ORIGINS: list[str] = []
DEV_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?$"
app.add_middleware(
    CORSMiddleware,
    allow_origins=PROD_ORIGINS,
    allow_origin_regex=DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)
