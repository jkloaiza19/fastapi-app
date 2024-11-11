from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import AsyncGenerator
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from db.interfaces import \
    DataBaseSessionInterface,\
    DataBaseInitializerInterface,\
    DataBaseSessionMakerInterface,\
    DataBaseEngineInterface,\
    DeclarativeBaseInterface
from core.logger import get_logger, LoggingLevelEnum
from core.config import settings

logger = get_logger(__name__)
max_tries = 60 * 5
wait_seconds = 10


@dataclass
class DataBaseEngine(DataBaseEngineInterface):
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=True)

    def get_engine(self) -> AsyncEngine:
        return self.engine


@dataclass
class DeclarativeBase(DeclarativeBaseInterface):
    base = declarative_base()

    def get_declarative_base(self):
        return self.base


class DataBaseSessionMaker(DataBaseSessionMakerInterface):
    def __init__(self, database_engine: DataBaseEngineInterface):
        self.engine = database_engine.get_engine()
        self.database_session = sessionmaker(
            bind=self.engine, class_=AsyncSession, autoflush=False
        )

    def get_session_maker(self) -> sessionmaker:
        return self.database_session


class DatabaseSession(DataBaseSessionInterface):
    def __init__(self, database_session: DataBaseSessionMakerInterface):
        self.async_session = database_session.get_session_maker()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_session() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(str(e))
                raise e
            finally:
                await session.close()


class DataBaseInitializer(DataBaseInitializerInterface):
    def __init__(self, engine: DataBaseEngineInterface, base: DeclarativeBaseInterface):
        self.engine = engine.get_engine()
        self.Base = base.get_declarative_base()

    @retry(
        stop=stop_after_attempt(max_tries),
        wait=wait_fixed(wait_seconds),
        before=before_log(logger, LoggingLevelEnum.INFO.value),
        after=after_log(logger, LoggingLevelEnum.WARN.value),
    )
    async def initialize_database(self):
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(self.Base.metadata.create_all)
        except Exception as e:
            logger.error(f"{e}")
            raise e


def get_declarative_base() -> DeclarativeBaseInterface:
    db_declarative_base = DeclarativeBase()
    return db_declarative_base


def get_database_session() -> DataBaseSessionInterface:
    database_engine = DataBaseEngine()
    database_session = DataBaseSessionMaker(database_engine)
    return DatabaseSession(database_session)


def get_database_initializer() -> DataBaseInitializerInterface:
    database_engine = DataBaseEngine()
    db_declarative_base = DeclarativeBase()
    return DataBaseInitializer(database_engine, db_declarative_base)
