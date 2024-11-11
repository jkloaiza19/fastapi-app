from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from core.logger import configure_logging, get_logger
from api.v1.main import v1_router
from db.database import get_database_initializer

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> None:
    logger.info("Starting application")
    configure_logging()
    await get_database_initializer().initialize_database()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(v1_router)


@app.get("/healthcheck")
def init():
    return {"result": "Success"}
