from typing import AsyncGenerator

from sqlalchemy.future import select
from core.logger import get_logger
from sqlalchemy.exc import DatabaseError, NoResultFound, SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from db.interfaces import DataBaseRepositoryInterface, DataBaseSessionInterface
from db.database import DatabaseSession, DataBaseSessionMaker
from db.models import User
from schemas.user_schema import UserRequest

logger = get_logger(__name__)


class UserRepository(DataBaseRepositoryInterface):
    # def __init__(self, session: AsyncSession):
    #     self.session = session

    async def get_all(self, limit: int = 0, offset: int = 0):
        try:
            stmt = select(User).limit(limit).offset(offset)
            result = await self.session.scalars(stmt)
            users = result.all()

            return users
        except DatabaseError as e:
            logger.error(f"{e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{e}")

    async def find_unique(self, **kwargs):
        if not kwargs:
            raise ValueError("At least one search parameter is required")

        try:
            stmt = select(User)
            for field, value in kwargs.items():
                stmt = stmt.where(getattr(User, field) == value)

            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            return user
        except NoResultFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        except AttributeError as e:
            logger.error(f"Invalid field specified: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def find_many(self, **kwargs):
        try:
            stmt = select(User)
            for field, value in kwargs.items():
                stmt = stmt.where(getattr(User, field) == value)

            result = await self.session.execute(stmt)
            users = result.scalars().all()

            if not users:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No users found")

            return users
        except AttributeError as e:
            logger.error(f"Invalid field specified: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Error fetching users: {e}")
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

    async def create_one(self, user: UserRequest) -> dict:
        try:
            new_user = User(**user.dict(exclude={"password"}))
            new_user.is_confirmed = False

            self.session.add(new_user)
            await self.session.commit()
            await self.session.refresh(new_user)

            return new_user.to_dict()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            ) from e


async def update_one(self, resource: UserRequest) -> User:
    """Update an existing user in the database."""
    try:
        stmt = select(User).where(User.id == resource.id)
        result = await self.session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {resource.id} not found"
            )

        for field, value in resource.dict(exclude_unset=True).items():
            setattr(existing_user, field, value)

        await self.session.commit()
        await self.session.refresh(existing_user)

        return existing_user

    except SQLAlchemyError as e:
        await self.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e}"
        ) from e
