import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSessionDep
from app.db.operations import sample
from app.schemas.problem import Problem

router = APIRouter(tags=["sheet"])


@router.get("/random")
async def random(
    session: DbSessionDep, problemset_id: uuid.UUID = Query(), n: int = Query(20)
) -> list[Problem]:
    return await sample(session, problemset_id, n)
