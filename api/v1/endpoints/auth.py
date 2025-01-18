from fastapi import APIRouter, status, BackgroundTasks, Request
from core.logger import get_logger
from schemas.user_schema import UserRequest
from typing import Dict
from api.dependencies import redis_dep
from api.dependencies import \
    http_client_dep, \
    aws_cognito_client_dep, \
    user_repository_dep, \
    email_client_dep, \
    auth_dependency, \
    redis_dep, \
    jwt_util_dep
from schemas.login_schema import SignUpRequest, TokenResponse, SignInRequest

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def signup(
        auth: auth_dependency,
        user: SignUpRequest,
        background_tasks: BackgroundTasks,
        aws_cognito_client: aws_cognito_client_dep,
        user_repository: user_repository_dep,
        email_client: email_client_dep,
        request: Request,
        jwt_util: jwt_util_dep
):
    return await auth.register_user(
        user=user,
        background_tasks=background_tasks,
        cognito_client=aws_cognito_client,
        user_repository=user_repository,
        email_client=email_client,
        request=request,
        jwt_util=jwt_util
    )


@router.get("/confirm_user/{token}", status_code=status.HTTP_200_OK, response_model=TokenResponse)
async def confirm_user(
        token: str,
        auth: auth_dependency,
        user_repository: user_repository_dep,
        cognito_client: aws_cognito_client_dep,
        request: Request,
        jwt_util: jwt_util_dep
):
    return await auth.confirm_user(
        token=token,
        user_repository=user_repository,
        cognito_client=cognito_client,
        request=request,
        jwt_util=jwt_util
    )


@router.post("/signin", status_code=status.HTTP_200_OK)
async def signin(
        auth: auth_dependency,
        user: SignInRequest,
        aws_cognito_client: aws_cognito_client_dep,
):
    return auth.sign_in(
        cognito_client=aws_cognito_client,
        user=user
    )
