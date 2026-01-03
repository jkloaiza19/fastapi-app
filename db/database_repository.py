from abc import ABC
from typing import AsyncGenerator, Type, TypeVar, Generic, Optional, List, Annotated
from sqlalchemy import func
from sqlalchemy.future import select
import json
from core.logger import get_logger
from sqlalchemy.exc import DatabaseError, NoResultFound, SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Depends
from db.interfaces import DataBaseRepositoryInterface
from db.database import get_database_session, database_session_dep
from services.redis.redis_client_interface import RedisClientInterface
from db.models import User, Comment, Notifications

T = TypeVar("T")
logger = get_logger(__name__)


class GenericDataBaseRepository(DataBaseRepositoryInterface, Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.__session = session
        self.__model = model
        
    @property
    def get_session(self) -> AsyncSession:
        return self.__session

    @property
    async def get_total_count(self) -> int:
        try:
            stmt = select(func.count()).select_from(self.__model)
            result = await self.__session.execute(stmt)
            total_count = result.scalar_one()
            return total_count
        except SQLAlchemyError as e:
            logger.error(f"Error fetching total count: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_all(self, limit: int = 0, offset: int = 0) -> List[T]:
        try:
            stmt = select(self.__model).limit(limit).offset(offset)
            result = await self.__session.scalars(stmt)
            return result.all()
        except DatabaseError as e:
            logger.error(f"{e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_many(self, **kwargs) -> List[T]:
        if not kwargs:
            raise ValueError("At least one search parameter is required")

        try:
            stmt = select(self.__model)
            for field, value in kwargs.items():
                stmt = stmt.where(getattr(self.__model, field) == value)

            result = await self.__session.execute(stmt)
            instances = result.scalars().all()

            if not instances:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records found")

            return instances
        except NoResultFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records found")
        except AttributeError as e:
            logger.error(f"Invalid field specified: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except SQLAlchemyError as e:
            logger.error(f"Error fetching records: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_unique(self, redis: Optional[RedisClientInterface] = None, **kwargs) -> Optional[T]:
        if not kwargs:
            raise ValueError("At least one search parameter is required")

        try:
            stmt = select(self.__model)
            for field, value in kwargs.items():
                stmt = stmt.where(getattr(self.__model, field) == value)

            result = await self.__session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

            info_to_cache = instance.to_dict()
            redis_key = f"{self.__model.__name__.lower()}-{kwargs['id']}" if "id" in kwargs else None

            if redis and redis_key:
                cached_data = await redis.get_cached_data(redis_key)

                if cached_data:
                    print("Cached data found")
                    return cached_data

                await redis.set_cache_data(redis_key, {
                    **info_to_cache,
                    **({"created_at": str(info_to_cache["created_at"])} if "created_at" in info_to_cache else {}),
                    **({"updated_at": str(info_to_cache["updated_at"])} if "updated_at" in info_to_cache else {})
                })

            return info_to_cache
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
            new_instance = self.__model(**data)
            self.__session.add(new_instance)
            await self.__session.commit()
            await self.__session.refresh(new_instance)
            return new_instance
        except SQLAlchemyError as e:
            await self.__session.rollback()
            logger.error(f"Error creating record: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def update_one(self, instance: T) -> T:
        try:
            await self.__session.commit()
            await self.__session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await self.__session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_by_query(self, query: str):
        try:
            stmt = text(query)
            result = await self.__session.execute(stmt)
            rows = result.fetchall()
            if not rows:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records found")
            return rows
        except SQLAlchemyError as e:
            logger.error(f"Error executing raw SQL query: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_user_repository(
        db_session: database_session_dep
) -> AsyncGenerator[GenericDataBaseRepository[User], None]:
    try:
        repository = GenericDataBaseRepository[User](db_session, User)
        yield repository
    except Exception as e:
        logger.error(f"Error initializing user repository: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_comments_repository(
        db_session: database_session_dep
) -> AsyncGenerator[GenericDataBaseRepository[Comment], None]:
    try:
        repository = GenericDataBaseRepository[Comment](db_session, Comment)
        yield repository
    except Exception as e:
        logger.error(f"Error initializing comments repository: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_notifications_repository(
        db_session: database_session_dep
) -> AsyncGenerator[GenericDataBaseRepository[Notifications], None]:
    try:
        repository = GenericDataBaseRepository[Notifications](db_session, Notifications)

        yield repository
    except Exception as e:
        logger.error(f"Error initializing notifications repository: {e}")
        raise e


user_repository_dep = Annotated[GenericDataBaseRepository, Depends(get_user_repository)]
comments_repository_dep = Annotated[GenericDataBaseRepository, Depends(get_comments_repository)]
notifications_repository_dep = Annotated[GenericDataBaseRepository, Depends(get_notifications_repository)]
