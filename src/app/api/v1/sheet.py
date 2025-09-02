import datetime
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.models import DBUser
from app.db.operations import ensure_user, query_problem, query_user, sample
from app.db.operations import report_attempt as report_attempt_db
from app.decos import in_session, in_transaction
from app.schemas.problem import Problem

router = APIRouter(tags=["sheet"])


@router.get("/random")
@in_session
@in_transaction
async def random(
    session: DbSessionDep, problemset_id: uuid.UUID = Query(), n: int = Query(20)
) -> list[Problem]:
    return await sample(session, problemset_id=problemset_id, n=n)


@router.get("/report")
@in_session
@in_transaction
async def report_attempt(
    session: DbSessionDep,
    problem_id: uuid.UUID = Query(),
    correct: bool = Query(),
    time: datetime.datetime | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
) -> Literal["ok"]:
    user: DBUser | None = None
    if user_id is None:
        user = await ensure_user(session, "anonymous")
    elif (user := await query_user(session, user_id=user_id)) is None:
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
