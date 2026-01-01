from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.api.deps import db as db_deps
from app.config import get_settings
from app.middlewares.exception_handler import register_exception_handlers
from app.utils.db import new_engine, new_session_getter


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    engine = new_engine(get_settings().database_url.get_secret_value())
    session_getter = new_session_getter(engine)
    db_deps.session_getter = session_getter
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(api_router, prefix="/api")

    register_exception_handlers(app)

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
    return app


app = create_app()
