from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import deps
from app.api import router as api_router
from app.config import settings
from app.db.utils import new_engine, new_session_getter


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    engine = new_engine(settings.database_url)
    session_getter = new_session_getter(engine)
    deps.session_getter = session_getter
    yield
    await engine.dispose()


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
