from fastapi import APIRouter

from . import deps
from .v1 import router as v1_router

__all__ = ["deps", "router"]

router = APIRouter()
router.include_router(v1_router, prefix="/v1")
