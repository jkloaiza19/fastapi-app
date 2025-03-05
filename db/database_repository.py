from abc import ABC
from typing import AsyncGenerator, Type, TypeVar, Generic, Optional, List, Annotated
from sqlalchemy.future import select
from core.logger import get_logger
from sqlalchemy.exc import DatabaseError, NoResultFound, SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Depends
from db.interfaces import DataBaseRepositoryInterface
from db.database import get_database_session
from services.redis.redis_client_interface import RedisClientInterface
from db.models import User

T = TypeVar("T")
logger = get_logger(__name__)


class GenericDataBaseRepository(DataBaseRepositoryInterface, ABC):
    def __init__(self, session: AsyncSession, model: any):
        self.session = session
        self.model = model

    async def get_all(self, limit: int = 0, offset: int = 0) -> List[T]:
        try:
            stmt = select(self.model).limit(limit).offset(offset)
            result = await self.session.scalars(stmt)
            return result.all()
        except DatabaseError as e:
            logger.error(f"{e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_unique(self, redis: Optional[RedisClientInterface] = None, **kwargs) -> Optional[T]:
        if not kwargs:
            raise ValueError("At least one search parameter is required")

        try:
            stmt = select(self.model)
            for field, value in kwargs.items():
                stmt = stmt.where(getattr(self.model, field) == value)

            result = await self.session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

            if redis and "id" in kwargs:
                await redis.set_cache_data(f"{self.model.__name__.lower()}-{kwargs['id']}", instance)

            return instance
        except NoResultFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        except AttributeError as e:
            logger.error(f"Invalid field specified: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error fetching record: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def create_one(self, data: dict) -> T:
        try:
            new_instance = self.model(**data)
            self.session.add(new_instance)
            await self.session.commit()
            await self.session.refresh(new_instance)
            return new_instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def update_one(self, instance: T) -> T:
        try:
            await self.session.commit()
            await self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_by_query(self, query: str):
        try:
            stmt = text(query)
            result = await self.session.execute(stmt)
            rows = result.fetchall()
            if not rows:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records found")
            return rows
        except SQLAlchemyError as e:
            logger.error(f"Error executing raw SQL query: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# async def get_generic_repository(model: Type[T]) -> AsyncGenerator[GenericDataBaseRepository[T], None]:
#     session = await get_database_session()
#     repository = GenericDataBaseRepository[model](session, model)
#     yield repository


async def get_user_repository() -> AsyncGenerator[GenericDataBaseRepository, None]:
    session = await get_database_session()
    repository = GenericDataBaseRepository(session, User)
    yield repository


user_repository_dep = Annotated[GenericDataBaseRepository, Depends(get_user_repository)]
