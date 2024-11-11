from abc import ABC, abstractmethod
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import sessionmaker


class DataBaseSessionInterface(ABC):
    @abstractmethod
    async def get_session(self) -> AsyncGenerator:
        pass


class DataBaseInitializerInterface(ABC):
    @abstractmethod
    async def initialize_database(self):
        pass


class DataBaseSessionMakerInterface(ABC):
    @abstractmethod
    def get_session_maker(self) -> sessionmaker:
        pass


class DataBaseEngineInterface(ABC):
    @abstractmethod
    def get_engine(self) -> AsyncEngine:
        pass


class DeclarativeBaseInterface(ABC):
    @abstractmethod
    def get_declarative_base(self):
        pass


