import datetime
from typing import Literal, Optional, AsyncGenerator
from fastapi import HTTPException, status
from abc import ABC, abstractmethod

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


class JWTUtilInterface(ABC):
    @abstractmethod
    def get_credentials_exception(self, detail: Optional[str] = "") -> HTTPException:
        pass

    @abstractmethod
    def get_password_hash(self, password: str) -> str:
        pass

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        pass

    @abstractmethod
    def generate_confirmation_token(self, sub: str) -> str:
        pass

    @abstractmethod
    def get_sub_from_token(self, token: str, type: Literal["access", "confirmation"]) -> str:
        pass


class JWTUtil(JWTUtilInterface):
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.confirmation_token_expire_minutes = 1440
        self.access_token_expire_hours = 1

    def get_credentials_exception(self, detail: Optional[str] = "") -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail or "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_access_token(self, sub: str):
        logger.info("Generating access token")
        try:
            expire = datetime.datetime.utcnow() + datetime.timedelta(
                hours=self.access_token_expire_hours
            )
            jwt_data = {"sub": sub, "exp": expire, "type": "access"}
            jwt_token = jwt.encode(
                jwt_data, key=settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
            )

            return jwt_token
        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            raise e

    def generate_confirmation_token(self, sub: str):
        logger.info("Generating confirmation token")
        try:
            expire = datetime.datetime.utcnow() + datetime.timedelta(
                minutes=self.confirmation_token_expire_minutes
            )
            jwt_data = {"sub": sub, "exp": expire, "type": "confirmation"}
            jwt_token = jwt.encode(
                jwt_data, key=settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
            )

            return jwt_token
        except Exception as e:
            logger.error(f"Error generating confirmation token: {e}")
            raise e

    def get_sub_from_token(self, token: str, type: Literal["access", "confirmation"]) -> str:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            email: str = payload.get("sub")
            token_type: str = payload.get("type")

            if email is None:
                raise self.get_credentials_exception("Could not find email in token")

            if token_type is None or token_type != type:
                raise self.get_credentials_exception("Invalid token type")

            return email
        except ExpiredSignatureError as e:
            raise self.get_credentials_exception("Token has expired") from e
        except JWTError as e:
            raise self.get_credentials_exception() from e


def get_jwt_util() -> AsyncGenerator[JWTUtilInterface, None]:
    try:
        jwt_util = JWTUtil()
        yield jwt_util
    except Exception as e:
        logger.error(f"{str(e)}")
        raise e