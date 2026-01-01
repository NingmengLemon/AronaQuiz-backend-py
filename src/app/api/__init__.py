from fastapi import APIRouter

from .deps import services
from .v1 import router as v1_router

__all__ = ["services", "router"]

router = APIRouter()
router.include_router(v1_router, prefix="/v1")
