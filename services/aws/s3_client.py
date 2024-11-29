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
from services.aws.aws_client import AWSClient, AwsServiceEnum

logger = get_logger(__name__)
FOLDER_NAME = "fastapi"


class AWSClientS3Interface(ABC):

    @abstractmethod
    async def upload_file_to_s3_bucket(self, file: UploadFile, folder: str = FOLDER_NAME) -> str:
        pass

    @abstractmethod
    async def get_signed_url(
            self,
            file_name: str, folder: str = FOLDER_NAME, expiration: int = 3600
    ) -> str:
        pass

    @abstractmethod
    async def delete_file_from_s3_bucket(self, file_name: str, folder: str = FOLDER_NAME) -> bool:
        pass

    @abstractmethod
    async def get_file_from_s3_bucket(
            self,
            file_name: str, folder: str = FOLDER_NAME
    ) -> StreamingResponse:
        pass

    @abstractmethod
    def close(self):
        pass


class AWSClientS3(AWSClientS3Interface):
    def __init__(self, aws_client: AWSClient):
        self.__client = aws_client.get_client()
        #     client(
        #     AwsServiceEnum.S3.value,
        #     region_name=settings.AWS_REGION,
        #     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        #     config=Config(retries={"max_attempts": 3, "mode": "standard"})
        # )

    async def get_signed_url(self, file_name: str, folder: str = FOLDER_NAME, expiration: int = 3600
    ) -> str:
        try:
            response = await to_thread(
                self.__client.generate_presigned_url,
                "get_object",
                Params={"Bucket": settings.AWS_BUCKET_NAME, "Key": f"{folder}/{file_name}"},
                ExpiresIn=expiration,
            )

            return response
        except Boto3Error as e:
            message = f"Error getting signed URL: {str(e)}"
            logger.error(message)
            raise HTTPException(status_code=500, detail=str(e))

    async def upload_file_to_s3_bucket(self, file: UploadFile, folder: str = FOLDER_NAME) -> str:
        try:
            content_type, _ = mimetypes.guess_type(file.filename)
            await to_thread(
                self.__client.upload_fileobj,
                file.file,
                settings.AWS_BUCKET_NAME,
                f"{FOLDER_NAME}/{file.filename}",
                ExtraArgs={"ACL": "public-read", "ContentType": content_type or "application/octet-stream"},
            )

            # file_url = f"https://{config.AWS_BUCKET_NAME}.s3.amazonaws.com/{folder}/{file.filename}"\
            file_url = await self.get_signed_url(file.filename, folder)

            logger.debug(f"File uploaded successfully. URL: {file_url}")

            return file_url
        except Boto3Error as e:
            message = f"Error uploading file to S3: {str(e)}"
            logger.error(message)
            raise HTTPException(status_code=500, detail=message)

    async def delete_file_from_s3_bucket(self, file_name: str, folder: str = FOLDER_NAME) -> bool:
        try:
            await to_thread(
                self.__client.delete_object,
                Bucket=settings.AWS_BUCKET_NAME,
                Key=f"{folder}/{file_name}",
            )

            return True
        except Boto3Error as e:
            message = f"Error deleting file from S3: {str(e)}"
            logger.error(message)
            raise HTTPException(status_code=500, detail=message)

    async def get_file_from_s3_bucket(self, file_name: str, folder: str = FOLDER_NAME) -> StreamingResponse:
        try:
            response = await to_thread(
                self.__client.get_object,
                Bucket=settings.AWS_BUCKET_NAME,
                Key=f"{folder}/{file_name}",
            )

            file_body = response["Body"]

            return StreamingResponse(file_body, media_type="application/octet-stream")
        except Boto3Error as e:
            message = f"Error getting file from S3: {str(e)}"
            logger.error(message)
            raise HTTPException(status_code=500, detail=message)

    def close(self):
        """Closes underlying endpoint connections"""
        self.__client.close()


def get_aws_s3_client() -> AsyncGenerator[AWSClientS3Interface, None]:
    aws_client = AWSClient(AwsServiceEnum.S3.value)
    s3_client = AWSClientS3(aws_client=aws_client)
    try:
        yield s3_client
    except Boto3Error as e:
        logger.error(f"Error getting file from S3: {str(e)}")
        raise e
    finally:
        s3_client.close()
