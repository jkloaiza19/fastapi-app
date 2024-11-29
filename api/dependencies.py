from http.client import HTTPException

from fastapi import Depends
from typing import Annotated, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from services.http.http_client import get_http_client, HttpClient
from db.database import \
    get_database_initializer,\
    DataBaseSessionInterface,\
    DataBaseInitializerInterface,\
    get_database_session_maker,\
    get_declarative_base,\
    DatabaseSession
from services.AI.chat_bot import get_chat_completion_service
from services.AI.interfaces import OpenAIInterface
from db.crud.user import UserRepository
from db.interfaces import DataBaseRepositoryInterface
from services.AI.interfaces import OpenAIInterface
from services.AI.chat_bot import ChatCompletion
from core.logger import get_logger

# AWS
from services.aws.s3_client import get_aws_s3_client, AWSClientS3Interface

logger = get_logger(__name__)

http_client_dep = Annotated[HttpClient, Depends(get_http_client)]
database_initializer_dep = Annotated[DataBaseInitializerInterface, Depends(get_database_initializer)]

# AWS Dependencies
aws_s3_client_dep = Annotated[AWSClientS3Interface, Depends(get_aws_s3_client)]


# AI Dependencies
def get_chat_completion_service(http_client: http_client_dep) -> AsyncGenerator[OpenAIInterface, None]:
    try:
        chat_completion = ChatCompletion(
            http_client=http_client,
        )
        yield chat_completion
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initialize AI service. {str(e)}")


chat_completion_dep = Annotated[OpenAIInterface, Depends(get_chat_completion_service)]


# Database Dependencies
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with DatabaseSession(get_database_session_maker()) as session:
        yield session


database_session_dep = Annotated[AsyncSession, Depends(get_database_session)]


async def get_user_repository(db_session: database_session_dep) -> AsyncGenerator[DataBaseRepositoryInterface, None]:
    user_repository = UserRepository(db_session)
    yield user_repository

user_repository_dep = Annotated[DataBaseRepositoryInterface, Depends(get_user_repository)]
