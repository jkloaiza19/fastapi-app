from fastapi import APIRouter, status, BackgroundTasks, Request
from core.logger import get_logger
from schemas.user_schema import UserRequest
from typing import Dict
from api.dependencies import redis_dep
from api.dependencies import \
    http_client_dep, \
    aws_cognito_client_dep, \
    email_client_dep, \
    auth_dependency, \
    redis_dep, \
    jwt_util_dep
from schemas.login_schema import SignUpRequest, TokenResponse, SignInRequest
from core.decorators.auth_decorator import token_required
from utils.general_util import get_limiter
from db.database_repository import user_repository_dep

logger = get_logger(__name__)
router = APIRouter()
limiter = get_limiter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""Register a new user account and send a confirmation email.
    
    **Rate limited to 5 requests per hour per IP address.**
    
    The endpoint will:
    - Create a new user in AWS Cognito
    - Store user information in the database
    - Send a confirmation email with verification link
    - Return user details upon successful registration
    
    The user must confirm their email before they can sign in.
    """,
)
@limiter.limit("5/hour")
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


@router.get(
    "/confirm_user/{token}",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Confirm user email",
    description="""Confirm a user's email address using the token sent via email.
    
    This endpoint:
    - Validates the confirmation token
    - Activates the user account in AWS Cognito
    - Marks the user as confirmed in the database
    - Returns authentication tokens (access token, refresh token, ID token)
    
    After confirmation, the user can sign in with their credentials.
    """,
    responses={
        200: {"description": "Email confirmed successfully. Returns authentication tokens."},
        400: {"description": "Invalid or expired token"},
        404: {"description": "User not found"}
    }
)
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


@router.post(
    "/signin",
    status_code=status.HTTP_200_OK,
    summary="Sign in user",
    description="""Authenticate a user and return access tokens.
    
    **Requirements:**
    - User must have confirmed their email address
    - Valid email and password required
    
    **Returns:**
    - Access token (JWT) - Use for authenticating API requests
    - Refresh token - Use to obtain new access tokens
    - ID token - Contains user claims and profile information
    - Expires in - Token expiration time in seconds
    
    Use the access token in the Authorization header: `Bearer <access_token>`
    """,
    responses={
        200: {"description": "Successfully authenticated. Returns authentication tokens."},
        401: {"description": "Invalid credentials or unconfirmed email"},
        404: {"description": "User not found"}
    }
)
async def signin(
        auth: auth_dependency,
        user: SignInRequest,
        aws_cognito_client: aws_cognito_client_dep,
):
    return auth.sign_in(
        cognito_client=aws_cognito_client,
        user=user
    )


@router.get(
    "/get_user",
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description="""Retrieve the currently authenticated user's profile information.
    
    **Authentication Required:** Bearer token in Authorization header
    
    Returns complete user profile including:
    - User ID and username
    - Email address
    - Account status (confirmed/unconfirmed)
    - Account creation and update timestamps
    - Cognito user attributes
    
    The user information is extracted from the validated JWT token.
    """,
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "User not found"}
    }
)
@token_required
async def get_user(
        request: Request,
        db: user_repository_dep,
        aws_cognito_client: aws_cognito_client_dep,
):
    return request.state.user
