from abc import ABC, abstractmethod
from enum import Enum
from asyncio import to_thread
from typing import Optional, AsyncGenerator
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import mimetypes
from boto3 import client
from boto3.exceptions import Boto3Error
from botocore.config import Config
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)
FOLDER_NAME = "fastapi"


class AwsServiceEnum(str, Enum):
    S3 = "s3"
    COGNITO = "cognito-idp"
    DYNAMODB = "dynamodb"
    IAM = "iam"


class AWSClientInterface(ABC):

    @abstractmethod
    def get_client(self):
        pass

    @abstractmethod
    def close(self):
        pass


class AWSClient(AWSClientInterface):
    def __init__(self, service: str):
        self.__client = client(
            service,
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=Config(retries={"max_attempts": 3, "mode": "standard"})
        )

    def get_client(self):
        return self.__client

    def close(self):
        self.__client.close()
