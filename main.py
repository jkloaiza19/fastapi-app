from fastapi import FastAPI
import sentry_sdk
# from sentry_sdk.integrations import FastAPIIntegration

# from sentry_sdk.integrations
# from sentry_sdk.integrations.asgi import SentryAsgiMiddlewa
from fastapi.concurrency import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.logger import configure_logging, get_logger
from core.config import settings
from db.database import get_database_initializer

# Routes
from api.v1.main import v1_router
from core.middlewares.request_logger_middleware import RequestLoggingMiddleware
from core.middlewares.cloudwatch_logs_middleware import CloudWatchLoggingMiddleware
# Middlewares
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from graphql_server.graphql_handler import graphql_app
from services.redis.initialize_redis import get_redis


logger = get_logger(__name__)

# sentry_sdk.init(dsn=settings.SENTRY_DNS)


sentry_sdk.init(
    dsn=settings.SENTRY_DNS,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    # integrations=[
    #     StrawberryIntegration(
    #         async_execution=True,
    #     ),
    # ],
)


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
app.middleware(CloudWatchLoggingMiddleware)
# app.add_middleware(SentryAsgiMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(v1_router)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/healthcheck")
def health_check():
    return {"result": "Success"}


handler = Mangum(app, lifespan="off")
