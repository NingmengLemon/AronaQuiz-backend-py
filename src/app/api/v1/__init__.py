from fastapi import APIRouter

from .problem import router as problem_router
from .stat import router as stat_router

router = APIRouter()
router.include_router(stat_router, prefix="/stat")
router.include_router(problem_router, prefix="/problem")
