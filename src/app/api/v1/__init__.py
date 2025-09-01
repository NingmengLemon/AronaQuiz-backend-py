from fastapi import APIRouter

from .problem import router as problem_router
from .sheet import router as sheet_router

router = APIRouter()
router.include_router(sheet_router, prefix="/sheet")
router.include_router(problem_router, prefix="/problem")
