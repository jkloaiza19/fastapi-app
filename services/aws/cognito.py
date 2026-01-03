from typing import Any, AsyncGenerator, Optional
from abc import ABC, abstractmethod
from boto3.exceptions import Boto3Error

from db.models import User
from schemas.login_schema import (
    RefreshTokenRequest,
    SignInRequest,
    SignUpRequest,
)
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from services.aws.aws_client import AwsServiceEnum
from services.http.http_client import HttpClientInterface, get_http_client, HttpClientSingleton
from db.interfaces import DataBaseRepositoryInterface
from services.redis.redis_client_interface import RedisClientInterface
from services.aws.aws_client import AWSClient
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


class CognitoClientInterface(ABC):
    @abstractmethod
    def sign_up(self, sign_up_data: SignUpRequest) -> bool:
        pass

    @abstractmethod
    def confirm_sign_up(self, username: str) -> bool:
        pass

    @abstractmethod
    def sign_in(self, sign_in_data: SignInRequest) -> dict[str, Any]:
        pass

    @abstractmethod
    def sign_out(self, access_token: str):
        pass

    @abstractmethod
    def refresh_token(self, refresh_token_data: RefreshTokenRequest):
        pass

    @abstractmethod
    async def get_cognito_public_keys(self) -> dict:
        pass

    @abstractmethod
    async def verify_token(
            self,
            token: str,
            db: DataBaseRepositoryInterface,
    ) -> dict:
        pass

    @abstractmethod
    async def get_current_user(
            self,
            token: str,
            db: DataBaseRepositoryInterface,
            redis: RedisClientInterface
    ):
        pass

    @abstractmethod
    def close(self):
        pass


class CognitoClient(CognitoClientInterface):
    def __init__(self, aws_client: AWSClient, http_client: HttpClientInterface):
        self.__client = aws_client.get_client()
        self.http_client = http_client
        self.cognito_algorithm = "RS256"

    def sign_up(self, sign_up_data: SignUpRequest) -> bool:
        try:
            response = self.__client.sign_up(
                ClientId=settings.COGNITO_CLIENT_ID,
                Username=sign_up_data.username,
                Password=sign_up_data.password,
                UserAttributes=[
                    {"Name": "email", "Value": sign_up_data.email},
                    {"Name": "given_name", "Value": sign_up_data.username},
                    {"Name": "family_name", "Value": sign_up_data.username},
                    {"Name": "name", "Value": sign_up_data.username},
                ],
            )

            return True if response["ResponseMetadata"]["HTTPStatusCode"] == 200 else False
        except self.__client.exceptions.UsernameExistsException as e:
            logger.error(f"Username already exists: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )
        except self.__client.exceptions.InvalidPasswordException as e:
            logger.error(f"Invalid password: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except self.__client.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    def confirm_sign_up(self, username: str) -> bool:
        try:
            response = self.__client.admin_confirm_sign_up(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username,
                # ConfirmationCode=confirmation_code,
            )

            return True if response["ResponseMetadata"]["HTTPStatusCode"] == 200 else False
        except self.__client.exceptions.UsernameExistsException as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except self.__client.exceptions.InternalErrorException as e:
            logger.error(f"Exception: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    def sign_in(self, sign_in_data: SignInRequest) -> dict[str, Any]:
        try:
            response = self.__client.initiate_auth(
                ClientId=settings.COGNITO_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": sign_in_data.username,
                    "PASSWORD": sign_in_data.password,
                },
            )

            return {
                "id_token": response["AuthenticationResult"]["IdToken"],
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "refresh_token": response["AuthenticationResult"]["RefreshToken"],
                "token_type": response["AuthenticationResult"]["TokenType"],
                "expires_in": response["AuthenticationResult"]["ExpiresIn"],
            }
        except self.__client.exceptions.NotAuthorizedException as e:
            logger.error(f"Not authorized: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )
        except self.__client.exceptions.UserNotConfirmedException as e:
            logger.error(f"User not confirmed: {e}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    def sign_out(self, access_token: str):
        try:
            response = self.__client.global_sign_out(
                AccessToken=access_token,
            )

            return response
        except self.__client.exceptions.NotAuthorizedException as e:
            logger.error(f"Not authorized: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
        except self.__client.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except self.__client.exceptions.ResourceNotFoundException as e:
            logger.error(f"Resource not found: {e}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    def refresh_token(self, refresh_token_data: RefreshTokenRequest):
        try:
            response = self.__client.initiate_auth(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": refresh_token_data.refresh_token,
                },
            )

            return {
                "id_token": response["AuthenticationResult"]["IdToken"],
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "token_type": response["AuthenticationResult"]["TokenType"],
                "expires_in": response["AuthenticationResult"]["ExpiresIn"],
            }
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    async def get_cognito_public_keys(self) -> dict:
        jwks = await self.http_client.get_request(settings.COGNITO_JWK_URL)
        return {key["kid"]: key for key in jwks["keys"]}

    async def verify_token(
            self,
            token: str,
            db: DataBaseRepositoryInterface,
    ) -> dict:
        try:
            unverified_headers = jwt.get_unverified_headers(token)
            kid = unverified_headers["kid"]
            response = await self.get_cognito_public_keys()
            public_key = response[kid]

            if public_key:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=[self.cognito_algorithm],
                    audience=settings.COGNITO_CLIENT_ID,
                    issuer=f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}",
                )

                user: User = await db.find_unique(None, username=payload["username"])

                return user.to_dict(exclude=["id"])
                # return user
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials: {str(e)}",
            )
        except ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token has expired: {str(e)}",
            )
        finally:
            self.close()

    async def get_current_user(
            self,
            token: str,
            db: DataBaseRepositoryInterface,
            redis: Optional[RedisClientInterface] = None
    ):
        try:
            response = self.__client.get_user(AccessToken=token)

            if response is None:
                raise self.__client.exceptions.NotAuthorizedException

            username = response["Username"]

            if username is None:
                raise self.__client.exceptions.UserNotFoundException

            user = await db.find_unique(redis, username=username)
            logger.debug(f"user: {user.to_dict(exclude=['id'])}")

            return user
        except self.__client.exceptions.NotAuthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
            )
        except self.__client.exceptions.UserNotFoundException as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except self.__client.exceptions.InvalidParameterException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    def close(self):
        self.__client.close()


async def get_aws_cognito_client() -> AsyncGenerator[CognitoClientInterface, None]:
    aws_client = AWSClient(AwsServiceEnum.COGNITO.value)
    http_client = HttpClientSingleton.get_instance()
    aws_cognito_client = CognitoClient(
        aws_client=aws_client,
        http_client=http_client,
    )
    try:
        yield aws_cognito_client
    except Boto3Error as e:
        logger.error(f"Error getting cognito service: {str(e)}")
        raise e
    finally:
        aws_cognito_client.close()
