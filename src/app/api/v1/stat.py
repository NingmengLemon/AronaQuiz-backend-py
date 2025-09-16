import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException

from app.api.deps import DbSessionDep, LoginRequired
from app.db.models import DBUser
from app.db.operations import query_problem, query_user
from app.db.operations import report_attempt as report_attempt_db

router = APIRouter(tags=["stat"])


@router.post(
    "/report",
    summary="上报答题情况",
    description="",
)
async def report_attempt(
    session: DbSessionDep,
    login_session: LoginRequired,
    problem_id: UUID = Body(),
    correct: bool = Body(),
    time: datetime.datetime | None = Body(None),
) -> Literal["ok"]:
    # TODO: 返回上报后的统计数据
    user: DBUser | None = None
    if (user := await query_user(session, user_id=login_session.user_id)) is None:
        raise HTTPException(404, "用户不存在")
    if (problem := await query_problem(session, problem_id=problem_id)) is None:
        raise HTTPException(404, "题目不存在")

    await report_attempt_db(
        session,
        problem_id=problem.id,
        user_id=user.id,
        correct=correct,
        time=time,
    )

    return "ok"
