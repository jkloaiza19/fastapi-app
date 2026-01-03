from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse
# from fastapi.websockets import WebSocket
import sentry_sdk
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# from sentry_sdk.integrations import FastAPIIntegration

# from sentry_sdk.integrations
# from sentry_sdk.integrations.asgi import SentryAsgiMiddlewa
from fastapi.concurrency import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.logger import configure_logging, get_logger
from core.config import settings
from db.database import get_database_initializer
from services.web_sockets.ws_manager import ws_manager_dep

# Routes
from api.v1.main import v1_router
from core.middlewares.request_logger_middleware import RequestLoggingMiddleware
from core.middlewares.cloudwatch_logs_middleware import CloudWatchLoggingMiddleware
from core.middlewares.security_headers_middleware import SecurityHeadersMiddleware

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

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
app.state.limiter = limiter

templates = Jinja2Templates(directory="api/templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Middlewares
app.middleware(RequestLoggingMiddleware)
app.middleware(CloudWatchLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
    status_code=429, content={"detail": "Rate limit exceeded"}
))
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


# Routes
app.include_router(v1_router)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/healthcheck")
@limiter.limit("5/minute")
def health_check(request: Request):
    return {"result": "Success"}


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onopen = () => {
              console.log("Connected");
              ws.send(JSON.stringify({ action: "hello" }));
            };
            ws.onmessage = function(event) {
                console.log("Received:", event.data);
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/websocket")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, ws_manager: ws_manager_dep):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print("Received data:", data)
            print("WebSocket connection established", ws_manager.active_connections)
            await websocket.send_text(f"Message text was: {data}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.close_connection(websocket)


handler = Mangum(app, lifespan="off")
