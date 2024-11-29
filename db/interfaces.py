from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker


class DataBaseSessionInterface(ABC):
    @abstractmethod
    async def get_session(self) -> AsyncSession:
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
    def get_model_base(self):
        pass


class DataBaseRepositoryInterface(ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def get_all(self, limit: int = 0, offset: int = 0):
        pass

    @abstractmethod
    async def find_many(self, **kwargs):
        pass

    @abstractmethod
    async def find_unique(self, **kwargs):
        pass

    @abstractmethod
    async def find_by_query(self, query: str):
        pass

    @abstractmethod
    async def create_one(self, resource):
        pass

    @abstractmethod
    async def update_one(self, resource):
        pass
