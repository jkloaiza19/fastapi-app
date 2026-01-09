from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi import BackgroundTasks, Request

from schemas.login_schema import SignUpRequest, SignInRequest
from core.logger import get_logger
from services.aws.cognito import CognitoClientInterface
from services.email.email_client import EmailClientInterface
from db.interfaces import DataBaseRepositoryInterface
from db.models import User
from utils.crypto_util import encrypt_data, decrypt_data
from utils.jwt_util import JWTUtilInterface
from utils.templates_util import TemplateType, get_template

logger = get_logger(__name__)


class AuthClientInterface(ABC):
    @abstractmethod
    async def register_user(
            self,
            user: SignUpRequest,
            background_tasks: BackgroundTasks,
            cognito_client: CognitoClientInterface,
            user_repository: DataBaseRepositoryInterface,
            email_client: EmailClientInterface,
            request: Request,
            jwt_util: JWTUtilInterface
    ) -> None:
        pass

    @abstractmethod
    async def confirm_user(
            self,
            token: str,
            user_repository: DataBaseRepositoryInterface,
            cognito_client: CognitoClientInterface,
            request: Request,
            jwt_util: JWTUtilInterface
    ) -> HTMLResponse:
        pass

    @abstractmethod
    def sign_in(self, user: SignInRequest, cognito_client: CognitoClientInterface) -> Dict:
        pass


class AuthClient(AuthClientInterface):
    async def register_user(
            self,
            user: SignUpRequest,
            background_tasks: BackgroundTasks,
            cognito_client: CognitoClientInterface,
            user_repository: DataBaseRepositoryInterface,
            email_client: EmailClientInterface,
            request: Request,
            jwt_util: JWTUtilInterface
    ) -> Dict:
        try:
            user_exists = await user_repository.find_unique(username=user.username)

            if user_exists:
                raise Exception("User already exists")

            cognito_client.sign_up(user)

            new_user = await user_repository.create_one(user.model_dump(exclude={"password"}))

            background_tasks.add_task(
                email_client.send_confirmation_email,
                user.email,
                user.username,
                request.url_for(
                    "confirm_user", token=jwt_util.generate_confirmation_token(user.username)
                ),
            )

            return new_user
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            raise e

    async def confirm_user(
            self,
            token: str,
            user_repository: DataBaseRepositoryInterface,
            cognito_client: CognitoClientInterface,
            request: Request,
            jwt_util: JWTUtilInterface
    ) -> HTMLResponse:
        try:
            username: str = jwt_util.get_sub_from_token(token=token, type="confirmation")
            cognito_client.confirm_sign_up(username=username)
            user: User = await user_repository.find_unique(username=username)
            user.is_confirmed = True
            await user_repository.update_one(user)

            template = get_template(
                template_name=TemplateType.CONFIRM_USER.value,
                request=request,
                context={"username": user.username}
            )

            return HTMLResponse(content=template.body)
        except HTTPException as e:
            logger.error(f"Error confirming user: {e}")
            raise e

    def sign_in(self, user: SignInRequest, cognito_client: CognitoClientInterface) -> Any:
        try:
            user_data = cognito_client.sign_in(user)
            return user_data
        except HTTPException as e:
            logger.error(f"Error signing in user: {e}")
            raise e


async def get_auth_client() -> AsyncGenerator[AuthClientInterface, None]:
    try:
        auth_client = AuthClient()
        yield auth_client
    except Exception as e:
        logger.error(f"Error getting auth client: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting auth client: {str(e)}")