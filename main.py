from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.logger import configure_logging, get_logger
from db.database import get_database_initializer

# Routes
from api.v1.main import v1_router
from core.middlewares.request_logger_middleware import RequestLoggingMiddleware
# Middlewares
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from services.redis.initialize_redis import get_redis


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage the lifespan of the application."""
    try:
        logger.info("Starting application...")

        # Initialize Redis
        # redis = get_redis()
        # redis.init_redis_service()
        # logger.info("Redis initialized successfully.")

        # Initialize Database
        db = get_database_initializer()
        await db.initialize_database()
        logger.info("Database initialized successfully.")

        # Configure Logging
        configure_logging()
        logger.info("Logging configured successfully.")

        yield

    except Exception as e:
        logger.error("Error during application startup: %s", e, exc_info=True)
        raise

    finally:
        logger.info("Shutting down application...")
        try:
            await db.close_database()
            logger.info("Database connection closed.")
        except Exception as e:
            logger.error("Error closing database: %s", e, exc_info=True)

        # try:
        #     await redis.close()
        #     logger.info("Redis connection closed.")
        # except Exception as e:
        #     logger.error("Error closing Redis: %s", e, exc_info=True)


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="api/templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Middlewares
app.middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(v1_router)


@app.get("/healthcheck")
def health_check():
    return {"result": "Success"}


handler = Mangum(app, lifespan="off")
