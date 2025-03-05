from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from api.dependencies import user_repository_dep
# from db.database_repository import user_repository_dep


async def get_context(
        request: Request,
        user_repository: user_repository_dep,
):
    return {
        'request': request,
        'user_repository': user_repository,
        # 'db': db
    }
