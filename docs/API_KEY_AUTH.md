# API Key Authentication

## Overview
The `@api_key_required` decorator provides simple API key authentication for protecting endpoints without requiring full OAuth/Cognito authentication.

## Setup

### 1. Generate API Keys
```bash
# Generate a secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure API Keys

#### Option A: Environment Variable (.env)
```bash
# Single key
API_KEYS=your-secret-api-key-here

# Multiple keys (comma-separated)
API_KEYS=key1-abc123,key2-def456,key3-ghi789
```

#### Option B: AWS Secrets Manager (Production)
Store API keys in AWS Secrets Manager and load them in your settings:
```json
{
  "API_KEYS": "key1-abc123,key2-def456"
}
```

## Usage

### Protect an Endpoint
```python
from fastapi import APIRouter, Request
from core.decorators.auth_decorator import api_key_required

router = APIRouter()

@router.post("/protected-endpoint")
@api_key_required
async def my_endpoint(request: Request):
    # The decorator validates the API key before this runs
    return {"message": "Success! You have access."}
```

### Making Requests

#### Using cURL
```bash
curl -X POST https://api.example.com/api/v1/AI/rag/ask \
  -H "X-API-Key: your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is FastAPI?"}'
```

#### Using Python requests
```python
import requests

headers = {
    "X-API-Key": "your-secret-api-key-here",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.example.com/api/v1/AI/rag/ask",
    headers=headers,
    json={"question": "What is FastAPI?"}
)
```

#### Using JavaScript/TypeScript
```javascript
const response = await fetch('https://api.example.com/api/v1/AI/rag/ask', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-secret-api-key-here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ question: 'What is FastAPI?' })
});
```

## Error Responses

### Missing API Key (401)
```json
{
  "detail": "X-API-Key header required"
}
```

### Invalid API Key (403)
```json
{
  "detail": "Invalid API key"
}
```

## Security Best Practices

1. **Never commit API keys to version control**
   - Use `.env` files (add to `.gitignore`)
   - Use AWS Secrets Manager in production

2. **Rotate keys regularly**
   - Generate new keys periodically
   - Update clients before removing old keys

3. **Use HTTPS only**
   - API keys sent over HTTP can be intercepted

4. **Monitor usage**
   - Check logs for invalid key attempts
   - Track which keys are being used

5. **Consider rate limiting**
   - Add throttling per API key
   - Prevent abuse

## When to Use API Key vs Token Auth

### Use API Key (`@api_key_required`) for:
- ✅ Service-to-service communication
- ✅ Simple authentication needs
- ✅ Internal tools and scripts
- ✅ Webhook endpoints
- ✅ Background jobs / scheduled tasks

### Use Token Auth (`@token_required`) for:
- ✅ User-facing applications
- ✅ Mobile apps
- ✅ Web applications with user sessions
- ✅ When you need user context
- ✅ OAuth/Cognito flows

## Examples in Your API

Protected endpoints:
- `POST /api/v1/AI/run-sync` - Notion sync endpoint
- `POST /api/v1/AI/rag/ask` - RAG question answering

## Combining with Other Auth

You can also create endpoints that accept either API key OR token:

```python
from fastapi import Request, HTTPException

async def flexible_auth(request: Request):
    # Try API key first
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key in _get_valid_api_keys():
        return {"auth_type": "api_key"}
    
    # Fall back to token auth
    token = request.headers.get("Authorization")
    if token:
        # Validate token...
        return {"auth_type": "token", "user": verified_user}
    
    raise HTTPException(401, "Authentication required")
```
