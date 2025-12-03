from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Secret
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)
from sqlalchemy import URL


class DatabaseConfig(BaseModel):
    drivername: str = "postgresql+asyncpg"
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    query: dict[str, list[str] | str] = {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=Path("arona_config.toml"),
        yaml_file=Path("arona_config.yaml") or Path("arona_config.yml"),
        yaml_file_encoding="utf-8",
        env_prefix="ARONA_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    debug: bool = False
    database: Secret[DatabaseConfig] = Secret(DatabaseConfig())
    test_database: Secret[DatabaseConfig | None] = Secret(None)

    @property
    def database_url(self) -> Secret[URL]:
        return Secret(URL.create(**self.database.get_secret_value().model_dump()))

    @property
    def test_database_url(self) -> Secret[URL] | None:
        if db := self.test_database.get_secret_value():
            return Secret(URL.create(**db.model_dump()))
        return None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
