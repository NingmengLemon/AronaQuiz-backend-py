from fastapi import APIRouter

from .auth import router as auth_router
from .problem import router as problem_router
from .stat import router as stat_router
from .user import router as user_router

router = APIRouter()
router.include_router(stat_router, prefix="/stat")
router.include_router(problem_router)
router.include_router(user_router)
router.include_router(auth_router, prefix="/auth")
