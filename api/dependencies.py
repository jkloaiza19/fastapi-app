from http.client import HTTPException
from fastapi.security import OAuth2PasswordBearer

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
from core.config import settings

# AWS
from services.aws.s3_client import get_aws_s3_client, AWSClientS3Interface
from services.aws.cognito import get_aws_cognito_client, CognitoClientInterface


# Redis
from services.redis.redis_client import RedisClient, get_redis_client
from services.redis.redis_client_interface import RedisClientInterface

# Email
from services.email.email_client import EmailClientInterface, get_email_client

# Endpoints
from services.auth import get_auth_client, AuthClientInterface

# Utils
from utils.jwt_util import JWTUtilInterface, get_jwt_util
from services.aws.open_search.open_search_client import OpenSearchClientInterface, get_opensearch_client

# AI
from services.AI.image_generator import get_image_generator_client, ImageGeneratorInterface

logger = get_logger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth_dependency = Annotated[str, Depends(oauth2_scheme)]

http_client_dep = Annotated[HttpClient, Depends(get_http_client)]
database_initializer_dep = Annotated[DataBaseInitializerInterface, Depends(get_database_initializer)]

# AWS Dependencies
aws_s3_client_dep = Annotated[AWSClientS3Interface, Depends(get_aws_s3_client)]
aws_cognito_client_dep = Annotated[CognitoClientInterface, Depends(get_aws_cognito_client)]
aws_open_search_client_dep = Annotated[OpenSearchClientInterface, Depends(get_opensearch_client)]

# Endpoints Dependencies
auth_dependency = Annotated[AuthClientInterface, Depends(get_auth_client)]


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
image_generator_dep = Annotated[ImageGeneratorInterface, Depends(get_image_generator_client)]


# Database Dependencies
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async with DatabaseSession(get_database_session_maker()) as session:
        yield session


database_session_dep = Annotated[AsyncSession, Depends(get_database_session)]


async def get_user_repository(db_session: database_session_dep) -> AsyncGenerator[DataBaseRepositoryInterface, None]:
    user_repository = UserRepository(db_session)
    yield user_repository

user_repository_dep = Annotated[DataBaseRepositoryInterface, Depends(get_user_repository)]

# Redis
redis_dep = Annotated[RedisClientInterface, Depends(get_redis_client)]

# Email
email_client_dep = Annotated[EmailClientInterface, Depends(get_email_client)]

# JWT
jwt_util_dep = Annotated[JWTUtilInterface, Depends(get_jwt_util)]

