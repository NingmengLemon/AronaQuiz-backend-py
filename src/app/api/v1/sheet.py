from fastapi import APIRouter, Query

from app.api.deps import DbSessionDep
from app.db.operations import sample
from app.schemas.sheet import Problem

router = APIRouter(tags=["sheet"])


@router.get("/random")
async def random(session: DbSessionDep, n: int = Query(20)) -> list[Problem]:
    return await sample(session, n)
