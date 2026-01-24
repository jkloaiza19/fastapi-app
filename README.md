# FastAPI Application

A production-ready FastAPI application with AI capabilities, OCR processing, GraphQL support, and comprehensive authentication features.

## 🚀 Features

### Core Features
- **FastAPI Framework** - High-performance async Python web framework
- **PostgreSQL Database** - Async database operations with SQLAlchemy 2.0
- **Authentication** - JWT-based authentication and API key support
- **GraphQL API** - Strawberry GraphQL integration
- **WebSocket Support** - Real-time communication capabilities
- **Rate Limiting** - SlowAPI integration for request throttling
- **Monitoring** - Sentry integration for error tracking and performance monitoring

### AI & ML Capabilities
- **OpenAI Integration** - Chat completion endpoints
- **RAG (Retrieval-Augmented Generation)** - Document retrieval and Q&A
- **OCR Processing** - Advanced OCR with Tesseract and EasyOCR
  - General document OCR
  - Specialized passport data extraction with MRZ parsing
  - PDF and image support
  - Multi-language support
- **LangChain Integration** - Advanced AI workflows
- **Vector Database** - AstraDB for semantic search

### Infrastructure
- **AWS Deployment** - Lambda support via Mangum and Zappa
- **Docker Support** - Containerized deployment
- **CloudWatch Logging** - AWS CloudWatch integration
- **Redis Caching** - Response caching and rate limiting
- **Database Migrations** - Alembic for schema management
- **Celery Tasks** - Distributed task processing

## 📋 Prerequisites

- Python 3.11+
- Poetry for dependency management
- PostgreSQL database
- Redis (for caching and rate limiting)
- AWS account (for deployment)

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd fastapi-app
```

### 2. Install dependencies
```bash
poetry install
```

### 3. Configure environment variables
Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=your-secret-key-here
API_KEYS=your-api-key-1,your-api-key-2

# AWS (Optional)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Sentry (Optional)
SENTRY_DNS=your-sentry-dsn

# AstraDB (Optional for RAG)
ASTRA_DB_API_ENDPOINT=your-astra-endpoint
ASTRA_DB_APPLICATION_TOKEN=your-astra-token

# Environment
ENVIRONMENT=dev
```

### 4. Run database migrations
```bash
poetry run alembic upgrade head
```

### 5. Start the development server
```bash
poetry run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **GraphQL Playground**: `http://localhost:8000/graphql`

### API Endpoints

#### Authentication (`/v1/auth`)
- `POST /v1/auth/register` - User registration
- `POST /v1/auth/signin` - User sign-in
- `GET /v1/auth/confirm_user/{token}` - Email confirmation
- `GET /v1/auth/get_user` - Get current user

#### User Management (`/v1/user`)
- `GET /v1/user/{user_id}` - Get user by ID
- `POST /v1/user/create` - Create new user

#### AI Services (`/v1/ai`)
- `POST /v1/ai/chat-completion` - OpenAI chat completion
- `POST /v1/ai/run-sync` - Run Notion sync (requires API key)
- `POST /v1/ai/rag/ask` - RAG-based question answering (requires API key)

#### OCR Services (`/v1/ai/ocr`)
- `POST /v1/ai/ocr/extract` - Extract text from images/PDFs
  - Supports: PNG, JPEG, TIFF, WebP, PDF
  - Multi-language support
  - Configurable preprocessing
  - Optional bounding box detection
  
- `POST /v1/ai/ocr/extract/passport` - Specialized passport extraction
  - Automatic MRZ (Machine Readable Zone) parsing
  - Structured data extraction (name, DOB, passport number, etc.)
  - High-accuracy passport-specific processing

#### Notifications (`/v1/notifications`)
- `GET /v1/notifications/all` - Get all notifications
- `GET /v1/notifications/{user_id}` - Get user notifications
- `POST /v1/notifications/send` - Send notification
- `POST /v1/notifications/update` - Update notification status

### OCR API Usage Examples

#### General OCR
```bash
curl -X POST "http://localhost:8000/v1/ai/ocr/extract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.jpg" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "return_boxes=false"
```

#### Passport OCR
```bash
curl -X POST "http://localhost:8000/v1/ai/ocr/extract/passport" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@passport.jpg" \
  -F "lang=eng"
```

Response includes:
```json
{
  "text": "full extracted text...",
  "passport_data": {
    "passport_number": "N1234567",
    "surname": "DOE",
    "given_names": "JOHN",
    "nationality": "USA",
    "date_of_birth": "1990-01-01",
    "sex": "M",
    "date_of_expiry": "2030-01-01",
    "mrz_line1": "P<USADOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<",
    "mrz_line2": "N1234567<USA9001011M3001011<<<<<<<<<<<<<<<0"
  }
}
```

## 🔐 Authentication

### JWT Authentication
Standard JWT-based authentication for user endpoints. Include the token in the `Authorization` header:
```
Authorization: Bearer your-jwt-token
```

### API Key Authentication
For AI and OCR endpoints, use API key authentication with the `X-API-Key` header:
```
X-API-Key: your-api-key
```

See [API Key Authentication Documentation](docs/API_KEY_AUTH.md) for more details.

## 🗄️ Database

### Models
- **User** - User accounts and profiles
- **Notification** - User notifications
- Custom models in `db/models.py`

### Migrations
```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## 🐳 Docker Deployment

### Build and run with Docker Compose
```bash
docker-compose up -d
```

### Build standalone
```bash
docker build -t fastapi-app .
docker run -p 8000:8000 fastapi-app
```

## ☁️ AWS Deployment

### Lambda Deployment with Zappa
```bash
# Initialize
poetry run zappa init

# Deploy
poetry run zappa deploy production

# Update
poetry run zappa update production
```

### CloudFormation Templates
Available in `cloudformation/`:
- `infra.yml` - Core infrastructure
- `database.yml` - RDS database
- `notion_sync_lambda.yml` - Lambda for Notion sync

## 📊 GraphQL API

Access GraphQL playground at `/graphql`

Example query:
```graphql
query {
  # Your GraphQL queries here
}
```

## 🔧 Development

### Project Structure
```
fastapi-app/
├── api/                    # API routes
│   └── v1/
│       ├── endpoints/      # API endpoints
│       └── main.py        # Router configuration
├── core/                   # Core functionality
│   ├── config.py          # Settings and configuration
│   ├── decorators/        # Custom decorators
│   ├── middlewares/       # Custom middlewares
│   └── logger.py          # Logging configuration
├── db/                     # Database
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # Database connection
│   └── crud/              # CRUD operations
├── services/              # Business logic
│   ├── AI/                # AI services
│   │   ├── ocr/           # OCR services
│   │   └── rag/           # RAG services
│   ├── redis/             # Redis integration
│   └── web_sockets/       # WebSocket handlers
├── schemas/               # Pydantic schemas
├── utils/                 # Utility functions
├── graphql_server/        # GraphQL implementation
├── tests/                 # Tests
├── alembic/               # Database migrations
└── main.py               # Application entry point
```

### Running Tests
```bash
poetry run pytest
```

### Code Style
```bash
# Format code
poetry run black .

# Lint
poetry run flake8
```

## 🔍 Monitoring

### Logs
- **CloudWatch**: Automatic logging to AWS CloudWatch (production)
- **Local**: Logs written to `api.log`

### Error Tracking
- **Sentry**: Real-time error tracking and performance monitoring
- Configure `SENTRY_DNS` in environment variables

### Rate Limiting
Default limits configured per endpoint. Modify in route decorators:
```python
@limiter.limit("5/minute")
async def endpoint():
    ...
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

[Your License Here]

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Contact: jkloaiza19@gmail.com

## 🔄 Version History

- **0.1.0** - Initial release
  - FastAPI core setup
  - Authentication system
  - OCR capabilities
  - GraphQL support
  - AWS deployment ready
