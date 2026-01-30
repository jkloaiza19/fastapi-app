# Development Guide

## Getting Started

### Prerequisites
- Python 3.11+
- Poetry (Python package manager)
- PostgreSQL 14+
- Redis 6+
- Git
- Docker (optional)

### Initial Setup

1. **Clone and navigate to the project**
```bash
git clone <repository-url>
cd fastapi-app
```

2. **Install Poetry** (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies**
```bash
poetry install
```

4. **Activate virtual environment**
```bash
poetry shell
```

5. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your local configuration
```

6. **Start required services**
```bash
# Using Docker Compose
docker-compose up -d postgres redis

# Or start manually
# PostgreSQL on port 5432
# Redis on port 6379
```

7. **Run database migrations**
```bash
poetry run alembic upgrade head
```

8. **Start development server**
```bash
poetry run uvicorn main:app --reload
```

## Project Structure

```
fastapi-app/
├── main.py                     # Application entry point
├── pyproject.toml             # Poetry dependencies
├── alembic.ini                # Alembic configuration
├── docker-compose.yml         # Docker services
├── Dockerfile                 # Container definition
│
├── api/                       # API layer
│   ├── dependencies.py        # Dependency injection
│   └── v1/
│       ├── main.py           # API version router
│       └── endpoints/        # Route handlers
│           ├── auth.py       # Authentication endpoints
│           ├── user.py       # User management
│           ├── AI.py         # AI services
│           ├── ocr.py        # OCR endpoints
│           └── notifications.py
│
├── core/                      # Core functionality
│   ├── config.py             # Application settings
│   ├── logger.py             # Logging configuration
│   ├── exceptions.py         # Custom exceptions
│   ├── decorators/           # Custom decorators
│   │   └── auth_decorator.py # API key auth
│   └── middlewares/          # Request/response middleware
│       ├── request_logger_middleware.py
│       ├── cloudwatch_logs_middleware.py
│       └── security_headers_middleware.py
│
├── db/                        # Database layer
│   ├── database.py           # Database connection
│   ├── models.py             # SQLAlchemy models
│   ├── interfaces.py         # Repository interfaces
│   ├── database_repository.py # Generic repository
│   └── crud/                 # CRUD operations
│
├── schemas/                   # Pydantic schemas
│   ├── AI.py                 # AI request/response schemas
│   ├── login_schema.py       # Authentication schemas
│   └── ...
│
├── services/                  # Business logic
│   ├── AI/                   # AI services
│   │   ├── ocr/             # OCR processing
│   │   │   ├── ocr2.py      # Main OCR logic
│   │   │   └── parsers2.py  # Passport parsing
│   │   └── rag/             # RAG implementation
│   ├── redis/               # Redis integration
│   └── web_sockets/         # WebSocket handlers
│
├── utils/                     # Utility functions
│   ├── notion_loader.py      # Notion integration
│   └── ...
│
├── graphql_server/           # GraphQL implementation
│   ├── graphql_handler.py   # GraphQL app
│   ├── context.py           # Request context
│   ├── schemas/             # GraphQL schemas
│   └── resolvers/           # Query/mutation resolvers
│
├── tests/                    # Test suite
│   ├── conftest.py          # Test configuration
│   └── ...
│
├── alembic/                  # Database migrations
│   └── versions/            # Migration files
│
├── docs/                     # Documentation
│   ├── API_KEY_AUTH.md
│   ├── OCR_API.md
│   ├── DEPLOYMENT.md
│   └── GRAPHQL.md
│
└── cloudformation/           # AWS infrastructure
    ├── infra.yml
    └── database.yml
```

## Development Workflow

### Creating a New Endpoint

1. **Define Pydantic schema** (in `schemas/`)
```python
# schemas/my_feature.py
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    name: str = Field(..., min_length=1)
    value: int = Field(..., ge=0)

class MyResponse(BaseModel):
    id: int
    name: str
    value: int
```

2. **Create database model** (if needed, in `db/models.py`)
```python
from sqlalchemy import Column, Integer, String
from db.database import Base

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    value = Column(Integer)
```

3. **Create migration**
```bash
poetry run alembic revision --autogenerate -m "Add my_models table"
poetry run alembic upgrade head
```

4. **Implement CRUD operations** (in `db/crud/`)
```python
# db/crud/my_crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import MyModel

async def create_my_model(db: AsyncSession, name: str, value: int):
    model = MyModel(name=name, value=value)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model

async def get_my_model(db: AsyncSession, model_id: int):
    result = await db.execute(
        select(MyModel).where(MyModel.id == model_id)
    )
    return result.scalar_one_or_none()
```

5. **Create endpoint** (in `api/v1/endpoints/`)
```python
# api/v1/endpoints/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_async_session
from schemas.my_feature import MyRequest, MyResponse
from db.crud.my_crud import create_my_model, get_my_model

router = APIRouter()

@router.post("/create", response_model=MyResponse)
async def create_item(
    request: MyRequest,
    db: AsyncSession = Depends(get_async_session)
):
    item = await create_my_model(db, request.name, request.value)
    return item

@router.get("/{item_id}", response_model=MyResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    item = await get_my_model(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

6. **Register router** (in `api/v1/main.py`)
```python
from api.v1.endpoints import my_feature

v1_router.include_router(
    my_feature.router,
    prefix="/v1/my-feature",
    tags=["my-feature"]
)
```

### Adding a Middleware

```python
# core/middlewares/my_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class MyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Before request
        print(f"Request: {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # After request
        print(f"Response: {response.status_code}")
        
        return response

# In main.py
from core.middlewares.my_middleware import MyMiddleware
app.add_middleware(MyMiddleware)
```

### Creating a Background Task

```python
# services/tasks/my_task.py
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def my_background_task(param):
    # Long-running task
    result = process_something(param)
    return result

# In endpoint
from services.tasks.my_task import my_background_task

@router.post("/process")
async def process(data: str):
    task = my_background_task.delay(data)
    return {"task_id": task.id}
```

## Code Quality Tools

The project uses multiple tools to ensure code quality and security.

### Development Dependencies

Install all dev dependencies:
```bash
poetry install --with dev
```

**Included Tools:**
- `black` - Code formatter (PEP 8 compliant)
- `isort` - Import statement sorter
- `flake8` - Linter and style checker
- `mypy` - Static type checker
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `httpx` - Async HTTP client for tests
- `bandit` - Security vulnerability scanner
- `safety` - Dependency vulnerability checker
- `pre-commit` - Git hook framework

### Running Quality Checks

```bash
# Format code
poetry run black .

# Sort imports
poetry run isort .

# Lint code
poetry run flake8 .

# Type check
poetry run mypy .

# Security scan
poetry run bandit -r . -x ./tests,./alembic

# Check dependencies
poetry run safety check

# Run all checks
poetry run pre-commit run --all-files
```

### Configuration Files

- `.flake8` - Flake8 linting rules
- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `pyproject.toml` - Tool configurations for Black, isort, mypy, pytest, coverage

### Pre-commit Hooks

Automatically run checks before each commit:

```bash
# Install hooks
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify -m "message"
```

**What runs on commit:**
1. Trailing whitespace removal
2. End-of-file fixing
3. YAML/JSON/TOML validation
4. Large file detection
5. Black formatting
6. isort import sorting
7. flake8 linting
8. mypy type checking
9. Bandit security scanning

## Testing

The project includes a comprehensive test suite with 32+ tests covering all major functionality.

### Test Coverage

**Test Files:**
- `tests/test_main.py` - Application core (health check, rate limiting, CORS, 404s)
- `tests/test_auth.py` - Authentication (API key validation, protected endpoints)
- `tests/test_users.py` - User CRUD operations
- `tests/test_ai.py` - AI service endpoints (chat completion, RAG)
- `tests/test_ocr.py` - OCR processing (image extraction, passport parsing)
- `tests/conftest.py` - Test fixtures and configuration

**Current Results:**
- 19/32 tests passing (59%)
- Core functionality: 8/8 tests passing (100%)
- See [TEST_RESULTS.md](../TEST_RESULTS.md) for detailed report

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=. --cov-report=html

# Run specific test file
poetry run pytest tests/test_main.py -v

# Run core tests (100% passing)
poetry run pytest tests/test_main.py tests/test_auth.py -v

# Run specific test
poetry run pytest tests/test_auth.py::test_valid_api_key

# Run with verbose output
poetry run pytest -v

# Run and stop on first failure
poetry run pytest -x

# Run with short traceback
poetry run pytest --tb=short
```

### Test Configuration

Tests use the following services:
- **PostgreSQL** - Test database (can be mocked)
- **Redis** - Cache service (can be mocked)
- **AsyncClient** - HTTP client for endpoint testing
- **pytest-asyncio** - Async test support

### Writing Tests

Follow the existing test patterns in the test suite:

```python
# tests/test_my_feature.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_item(client: AsyncClient):
    """Test creating an item."""
    response = await client.post(
        "/v1/my-feature/create",
        json={"name": "test", "value": 42}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test"
    assert data["value"] == 42

@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """Test 404 for non-existent item."""
    response = await client.get("/v1/my-feature/999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_protected_endpoint(client: AsyncClient, auth_headers: dict):
    """Test API key authentication."""
    # Without auth
    response = await client.get("/v1/protected-endpoint")
    assert response.status_code == 401
    
    # With auth
    response = await client.get("/v1/protected-endpoint", headers=auth_headers)
    assert response.status_code == 200
```

### Test Fixtures

The `tests/conftest.py` file provides shared fixtures:

```python
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Setup tables
    base_interface = get_declarative_base()
    Base = base_interface.get_model_base()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture
def auth_headers() -> dict:
    """Provide authentication headers."""
    return {"X-API-Key": "test-api-key-1"}
```

## Database Management

### Creating Migrations
```bash
# Auto-generate migration from model changes
poetry run alembic revision --autogenerate -m "Description"

# Create empty migration
poetry run alembic revision -m "Description"

# Edit the generated file in alembic/versions/
```

### Applying Migrations
```bash
# Upgrade to latest
poetry run alembic upgrade head

# Upgrade to specific revision
poetry run alembic upgrade abc123

# Downgrade one version
poetry run alembic downgrade -1

# Downgrade to specific revision
poetry run alembic downgrade abc123

# Show current version
poetry run alembic current

# Show migration history
poetry run alembic history
```

### Database Seeding

```python
# scripts/seed.py
import asyncio
from db.database import get_async_session
from db.crud.user_crud import create_user

async def seed_data():
    async for session in get_async_session():
        # Create test users
        await create_user(
            session,
            email="admin@example.com",
            username="admin",
            password="admin123"
        )
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

Run seeding:
```bash
poetry run python scripts/seed.py
```

## Code Quality

### Linting
```bash
# Install development dependencies
poetry install --with dev

# Run flake8
poetry run flake8 .

# Run mypy (type checking)
poetry run mypy .

# Run black (formatting)
poetry run black .

# Run isort (import sorting)
poetry run isort .
```

### Pre-commit Hooks
```bash
# Install pre-commit
poetry add --group dev pre-commit

# Set up hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

## Debugging

### Using Python Debugger
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() in Python 3.7+
breakpoint()
```

### VS Code Debug Configuration
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Logging
```python
from core.logger import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

## Environment Variables

### Development (.env)
```bash
ENVIRONMENT=dev
DEBUG=true
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fastapi_dev

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=dev-secret-key-change-in-production
API_KEYS=dev-api-key-1,dev-api-key-2

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# AWS (optional for local dev)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Disable in dev
SENTRY_DNS=
```

## Performance Monitoring

### Local Profiling
```bash
# Install py-spy
pip install py-spy

# Profile running application
py-spy top --pid <process-id>

# Generate flamegraph
py-spy record -o profile.svg --pid <process-id>
```

### Database Query Monitoring
```python
# Enable SQL logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Common Tasks

### Reset Database
```bash
# Drop and recreate
poetry run alembic downgrade base
poetry run alembic upgrade head

# Or use script
poetry run python scripts/reset_db.py
```

### Update Dependencies
```bash
# Update all dependencies
poetry update

# Update specific package
poetry update package-name

# Check for outdated packages
poetry show --outdated
```

### Generate API Documentation
```bash
# FastAPI auto-generates docs at /docs and /redoc
# To export OpenAPI schema:
curl http://localhost:8000/openapi.json > openapi.json
```

## Troubleshooting

### Common Issues

**Issue: Poetry install fails**
```bash
# Clear cache
poetry cache clear pypi --all

# Reinstall
poetry install
```

**Issue: Database connection fails**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
# Verify credentials and database exists
```

**Issue: Redis connection fails**
```bash
# Check Redis is running
redis-cli ping

# Should return PONG
```

**Issue: Import errors**
```bash
# Ensure virtual environment is activated
poetry shell

# Reinstall dependencies
poetry install
```

## Best Practices

1. **Always use type hints**
2. **Write tests for new features**
3. **Keep endpoints focused and small**
4. **Use dependency injection**
5. **Handle errors gracefully**
6. **Log important events**
7. **Document complex logic**
8. **Use async/await properly**
9. **Validate input data**
10. **Keep secrets out of code**

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
