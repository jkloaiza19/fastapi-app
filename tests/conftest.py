"""
Test configuration and fixtures for the FastAPI application.
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment variables before importing the app
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
os.environ["ASYNC_DATABASE_URL_EXT"] = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["API_KEYS"] = "test-api-key-1,test-api-key-2"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["ENCRYPTION_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing-only"
os.environ["COGNITO_CLIENT_ID"] = "test-cognito-client-id"
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id"
os.environ["COGNITO_JWK_URL"] = "https://cognito-idp.us-east-1.amazonaws.com/test/.well-known/jwks.json"
os.environ["ASTRA_DB_API_ENDPOINT"] = "https://test-astra-endpoint.apps.astra.datastax.com"

from main import app
from db.database import get_declarative_base
from db.models import User


# Test database URL
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Get the declarative base
    base_interface = get_declarative_base()
    Base = base_interface.get_model_base()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with unique email per test."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        email=f"test-{unique_id}@example.com",
        username=f"testuser-{unique_id}",
        is_confirmed=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def api_key() -> str:
    """Return a valid test API key."""
    return "test-api-key-1"


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client to avoid real API calls."""
    from unittest.mock import Mock, MagicMock, AsyncMock
    
    # Mock the retrieve function to return empty docs
    async def mock_retrieve(question: str):
        return []
    
    monkeypatch.setattr("api.v1.endpoints.AI.retrieve", mock_retrieve)
    
    return mock_retrieve


@pytest.fixture
def mock_astra_db(monkeypatch):
    """Mock Astra DB to avoid real database calls."""
    from unittest.mock import MagicMock
    
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.get_collection.return_value = mock_collection
    
    # Mock the AstraDBVectorStore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = []
    
    monkeypatch.setattr("services.AI.rag.rag.AstraDBVectorStore", lambda *args, **kwargs: mock_vectorstore)
    
    return mock_db


@pytest.fixture
def mock_http_client(monkeypatch):
    """Mock HTTP client for AI services."""
    from unittest.mock import AsyncMock, Mock
    from openai.types.chat import ChatCompletionMessage
    
    # Create a mock HTTP client that returns the expected response structure
    async def mock_post_request(*args, **kwargs):
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Mocked AI response"
                }
            }]
        }
    
    # Patch the HttpClient.post_request method
    monkeypatch.setattr(
        "services.http.http_client.HttpClient.post_request",
        mock_post_request
    )
    
    # Also mock the module-level OpenAI client
    mock_message = ChatCompletionMessage(
        role="assistant",
        content="Mocked AI response"
    )
    
    mock_choice = Mock()
    mock_choice.message = mock_message
    
    mock_completion = Mock()
    mock_completion.choices = [mock_choice]
    
    mock_chat = Mock()
    mock_chat.completions = Mock()
    mock_chat.completions.create = Mock(return_value=mock_completion)
    
    mock_openai_client = Mock()
    mock_openai_client.chat = mock_chat
    
    monkeypatch.setattr("services.AI.chat_bot.client", mock_openai_client)
    
    return mock_post_request


@pytest.fixture
def auth_headers(api_key: str) -> dict:
    """Return headers with API key authentication."""
    return {"X-API-Key": api_key}
