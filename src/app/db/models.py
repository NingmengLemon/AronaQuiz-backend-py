from datetime import datetime, timedelta
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Awaitable, Generic
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.ext.asyncio.session import AsyncAttrs as _AsyncAttrs
from sqlmodel import Field, Relationship, SQLModel

from app.typ import T
from app.utils.uuid7 import uuid7

ACCESS_TOKEN_LIFETIME = 14  # days
REFRESH_TOKEN_LIFETIME = 120  # days


class AsyncAttrs(_AsyncAttrs, Generic[T]):
    if TYPE_CHECKING:
        awaitable_attrs: T  # type: ignore


class ProblemType(StrEnum):
    single_select = auto()
    multi_select = auto()


class _OptionAsyncAttrs:
    problem: Awaitable["DBProblem"]


class DBOption(SQLModel, AsyncAttrs[_OptionAsyncAttrs], table=True):
    __tablename__ = "option"  # type: ignore
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    order: int
    content: str
    is_correct: bool

    problem_id: UUID = Field(
        foreign_key="problem.id",
        # sa_column_kwargs={"ondelete": "CASCADE"},
    )
    problem: "DBProblem" = Relationship(back_populates="options")


class _ProblemAsyncAttrs:
    options: Awaitable[list[DBOption]]
    problemset: Awaitable["DBProblemSet"]


class DBProblem(SQLModel, AsyncAttrs[_ProblemAsyncAttrs], table=True):
    __tablename__ = "problem"  # type: ignore
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    content: str
    type: ProblemType

    problemset_id: UUID = Field(foreign_key="problemset.id")
    problemset: "DBProblemSet" = Relationship(back_populates="problems")
    options: list[DBOption] = Relationship(
        back_populates="problem",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class _ProblemSetAsyncAttrs:
    problems: Awaitable[list[DBProblem]]


class DBProblemSet(SQLModel, AsyncAttrs[_ProblemSetAsyncAttrs], table=True):
    __tablename__ = "problemset"  # type: ignore
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    name: str

    problems: list[DBProblem] = Relationship(
        back_populates="problemset",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class UserRole(StrEnum):
    USER = auto()  # permission level: min
    ADMIN = auto()
    SU = auto()  # permission level: max


class DBUser(SQLModel, table=True):
    __tablename__ = "user"  # type: ignore
    # 所有属性都无需二次 await 所以没写
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    email: EmailStr = Field(unique=True)
    username: str = Field(unique=True)
    password_hash: str
    nickname: str = Field(unique=True)
    role: UserRole = UserRole.USER


class DBAnswerRecord(SQLModel, table=True):
    __tablename__ = "answer_record"  # type: ignore
    __table_args__ = (PrimaryKeyConstraint("user_id", "problem_id"),)
    user_id: UUID = Field(foreign_key="user.id")
    problem_id: UUID = Field(foreign_key="problem.id")

    correct_count: int = 0
    total_count: int = 0
    last_attempt: datetime = Field(default_factory=lambda: datetime.fromtimestamp(0))


class LoginSessionStatus(StrEnum):
    ACTIVE = auto()  # session ok
    REVOKED = auto()  # operated by user themselves
    KICKED = auto()  # operated by security sys or admins
    EXPIRED = auto()  # also judged by <expires_at> field
    INVALID = auto()  # for other invalid conditions


class LoginSession(SQLModel, table=True):
    __tablename__ = "login_session"  # type: ignore
    id: UUID = Field(default_factory=uuid7, primary_key=True)

    access_token: UUID = Field(default_factory=uuid4)
    user_id: UUID = Field(foreign_key="user.id")

    expires_at: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(days=30)
    )
    created_at: datetime = Field(default_factory=datetime.now)
    last_renewal: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    status: LoginSessionStatus = LoginSessionStatus.ACTIVE

    device_info: str = ""
    refresh_token_hash: str
    refresh_token_expires_at: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(days=120)
    )
    # refresh token rotate 时, 创建一个新的 session, 将当前 session 设为 expired
    # 定期移除过旧的过期的 session


TABLES = [
    SQLModel.metadata.tables[t.__tablename__]  # type: ignore
    for t in (
        DBOption,
        DBProblem,
        DBProblemSet,
        DBUser,
        DBAnswerRecord,
        LoginSession,
    )
]
