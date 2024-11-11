import logging
from logging import Logger
from logging.config import dictConfig
from enum import Enum
from fastapi import Request

from core.config import settings


class LoggingLevelEnum(int, Enum):
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LoggingService:
    def __init__(self):
        self.__loger = logging.getLogger(__name__)

    def set_logger_name(self, logger_name: str):
        self.__loger.__setattr__("name", logger_name)

    def logger(self) -> Logger:
        return self.__loger

    def debug(self, content: str):
        return self.__loger.debug(content)

    def info(self, content: str):
        return self.__loger.info(content)

    def error(self, content: str):
        return self.__loger.error(content)

    def critical(self, content: str):
        return self.__loger(content)


def get_logger(name: str) -> Logger:
    return logging.getLogger(name)


def get_logger_dependency() -> LoggingService:
    return LoggingService()


# def obfuscated(email: str, obfuscated_length: int) -> str:
#     characters = email[:obfuscated_length]
#     first, last = email.split("@")
#     return characters + ("*" * (len(first) - obfuscated_length)) + "@" + last
#
#
# class EmailObfuscationFilter(logging.Filter):
#     def __init__(self, name: str = "", obfuscated_length: int = 2) -> None:
#         super().__init__(name)
#         self.obfuscated_length = obfuscated_length
#
#     def filter(self, record: logging.LogRecord) -> bool:
#         if "email" in record.__dict__:
#             record.email = obfuscated(record.email, self.obfuscated_length)
#         return True


def configure_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {
                "class": "logging.Formatter",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                # "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                # "format": "(%(correlation_id)s) - %(name)s line: %(lineno)d - %(message)s",
                "format": "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
            },
            "file": {
                "class": "logging.Formatter",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "format": "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "class": "rich.logging.RichHandler",  # "logging.StreamHandler",
                "formatter": "console",
                "level": "DEBUG",
            },
            "rotating_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file",
                "filename": "api.log",
                "maxBytes": 1024 * 1024 * 5,
                "backupCount": 5,
                "level": "DEBUG",
                "encoding": "utf8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default", "rotating_file"], "level": "INFO", "propagate": False},
            "api": {
                "handlers": ["default"],
                "level": "DEBUG" if settings.is_local_environment() else "INFO",
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["default", "rotating_file"],
                "level": "DEBUG" if settings.is_local_environment() else "INFO",
                "propagate": False
            },
            "databases": {"handlers": ["default"], "level": "WARNING"},
            "aiosqlite": {"handlers": ["default"], "level": "WARNING"},
        },
    })
