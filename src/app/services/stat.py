"""统计业务逻辑服务层"""

import logging

from app.utils.db import in_readonly_transaction

logger = logging.getLogger("uvicorn.error")


class StatService:
    """统计业务服务"""

    def __init__(self) -> None:
        pass
