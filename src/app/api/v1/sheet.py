import datetime
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSessionDep
from app.db.decos import in_session, in_transaction
from app.db.models import DBUser
from app.db.operations import ensure_user, query_problem, query_user, sample
from app.db.operations import report_attempt as report_attempt_db
from app.schemas.problem import ProblemSubmit

router = APIRouter(tags=["sheet"])


@router.get("/random", summary="随机抽取n道题目")
@in_session
@in_transaction()
async def random(
    session: DbSessionDep, problemset_id: uuid.UUID = Query(), n: int = Query(20)
) -> list[ProblemSubmit]:
    return await sample(session, problemset_id=problemset_id, n=n)


@router.get(
    "/report",
    summary="上报答题情况",
    description="""用户id 留空时计入 anonymous 用户""",
)
@in_session
@in_transaction()
async def report_attempt(
    session: DbSessionDep,
    problem_id: uuid.UUID = Query(),
    correct: bool = Query(),
    time: datetime.datetime | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
) -> Literal["ok"]:
    # TODO: 上报完毕后返回当前正确情况统计数据
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
