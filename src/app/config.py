from pydantic_settings import BaseSettings, SettingsConfigDict

INMEM_SQLITE_URL = "sqlite+aiosqlite://"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = INMEM_SQLITE_URL
    test_database_url: str = INMEM_SQLITE_URL


settings = Settings()
