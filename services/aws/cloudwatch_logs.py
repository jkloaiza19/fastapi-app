from abc import ABC, abstractmethod
from typing import AsyncGenerator

from boto3.exceptions import Boto3Error
from core.config import settings
from core.logger import get_logger
from services.aws.aws_client import AWSClient, AwsServiceEnum

logger = get_logger(__name__)


class CloudWatchLogsClientInterface(ABC):
    @abstractmethod
    def get_exceptions(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def create_log_group(self, log_group_name: str):
        pass

    @abstractmethod
    def delete_log_group(self, log_group_name: str):
        pass

    @abstractmethod
    def create_log_stream(self, log_group_name: str, log_stream_name: str):
        pass

    @abstractmethod
    def delete_log_stream(self, log_group_name: str, log_stream_name: str):
        pass

    @abstractmethod
    def put_log_events(self, log_group_name: str, log_stream_name: str, log_events: list):
        pass


class CloudWatchLogsClient(CloudWatchLogsClientInterface):
    def __init__(self, client: AWSClient):
        self.__client = client

    def get_exceptions(self):
        return self.__client.exceptions

    def close(self):
        self.__client.close()

    def create_log_group(self, log_group_name: str):
        try:
            return self.__client.create_log_group(logGroupName=log_group_name)
        except Boto3Error as e:
            logger.error(f"Error creating log group: {str(e)}")
            raise e

    def delete_log_group(self, log_group_name: str):
        try:
            return self.__client.delete_log_group(logGroupName=log_group_name)
        except Boto3Error as e:
            logger.error(f"Error deleting log group: {str(e)}")
            raise e

    def create_log_stream(self, log_group_name: str, log_stream_name: str):
        try:
            return self.__client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
        except Boto3Error as e:
            logger.error(f"Error creating log stream: {str(e)}")
            raise e

    def delete_log_stream(self, log_group_name: str, log_stream_name: str):
        try:
            return self.__client.delete_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
        except Boto3Error as e:
            logger.error(f"Error deleting log stream: {str(e)}")
            raise e

    def put_log_events(self, log_group_name: str, log_stream_name: str, log_events: list):
        try:
            return self.__client.put_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                logEvents=log_events
            )
        except Boto3Error as e:
            logger.error(f"Error putting log events: {str(e)}")
            raise e


def get_cloudwatch_logs_client() -> CloudWatchLogsClientInterface:
    aws_client = AWSClient(AwsServiceEnum.LOGS.value)
    return CloudWatchLogsClient(aws_client.get_client())


async def get_cloudwatch_logs_client_generator() -> AsyncGenerator[CloudWatchLogsClientInterface, None]:
    try:
        aws_cloudwatch_logs_client = get_cloudwatch_logs_client()
        yield aws_cloudwatch_logs_client
    finally:
        aws_cloudwatch_logs_client.close()
