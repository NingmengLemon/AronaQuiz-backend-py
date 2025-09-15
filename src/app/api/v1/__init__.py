from fastapi import APIRouter

from .problem import router as problem_router
from .session import router as session_router
from .stat import router as stat_router
from .user import router as user_router

router = APIRouter()
router.include_router(stat_router, prefix="/stat")
router.include_router(problem_router, prefix="/problem")
router.include_router(user_router, prefix="/user")
router.include_router(session_router, prefix="/session")
