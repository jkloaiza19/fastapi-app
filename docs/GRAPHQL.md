# GraphQL API Documentation

## Overview
The FastAPI application includes a GraphQL API powered by Strawberry GraphQL, providing a flexible alternative to REST endpoints.

## Access GraphQL

### GraphQL Playground
Interactive GraphQL IDE available at:
```
http://localhost:8000/graphql
```

In production:
```
https://your-domain.com/graphql
```

## Configuration

GraphQL is integrated in `main.py`:
```python
from graphql_server.graphql_handler import graphql_app

app.include_router(graphql_app, prefix="/graphql")
```

## Schema Structure

The GraphQL implementation is located in:
```
graphql_server/
├── graphql_handler.py    # Main GraphQL app configuration
├── context.py            # Request context (auth, database, etc.)
├── schemas/              # GraphQL type definitions
└── resolvers/            # Query and mutation resolvers
```

## Basic Usage

### Making a Query

Using cURL:
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { hello }"
  }'
```

Using Python:
```python
import requests

query = """
query {
  hello
}
"""

response = requests.post(
    "http://localhost:8000/graphql",
    json={"query": query}
)

print(response.json())
```

Using JavaScript:
```javascript
const query = `
  query {
    hello
  }
`;

const response = await fetch('http://localhost:8000/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ query })
});

const data = await response.json();
console.log(data);
```

## Authentication with GraphQL

### Using Context

GraphQL queries can access request context including authentication:

```python
# In context.py
from fastapi import Request
import strawberry

async def get_context(request: Request):
    return {
        "request": request,
        "user": await get_current_user(request),
        "db": request.app.state.db
    }

# In resolver
@strawberry.type
class Query:
    @strawberry.field
    async def me(self, info: strawberry.Info) -> User:
        user = info.context["user"]
        if not user:
            raise Exception("Not authenticated")
        return user
```

### Using Headers

Include authentication in headers:
```javascript
const response = await fetch('http://localhost:8000/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-jwt-token',
    // or
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({ query })
});
```

## Example Schemas and Resolvers

### Defining Types

```python
# In schemas/user.py
import strawberry
from typing import Optional

@strawberry.type
class User:
    id: int
    email: str
    username: str
    is_active: bool
    created_at: str

@strawberry.type
class UserResponse:
    success: bool
    user: Optional[User]
    message: Optional[str]
```

### Defining Queries

```python
# In resolvers/user_queries.py
import strawberry
from typing import List, Optional

@strawberry.type
class Query:
    @strawberry.field
    async def user(self, info: strawberry.Info, id: int) -> Optional[User]:
        """Get user by ID"""
        db = info.context["db"]
        user = await db.get_user(id)
        return user
    
    @strawberry.field
    async def users(self, info: strawberry.Info, limit: int = 10) -> List[User]:
        """Get all users"""
        db = info.context["db"]
        users = await db.get_users(limit=limit)
        return users
```

### Defining Mutations

```python
# In resolvers/user_mutations.py
import strawberry

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(
        self,
        info: strawberry.Info,
        email: str,
        username: str,
        password: str
    ) -> UserResponse:
        """Create a new user"""
        try:
            db = info.context["db"]
            user = await db.create_user(
                email=email,
                username=username,
                password=password
            )
            return UserResponse(
                success=True,
                user=user,
                message="User created successfully"
            )
        except Exception as e:
            return UserResponse(
                success=False,
                user=None,
                message=str(e)
            )
    
    @strawberry.mutation
    async def update_user(
        self,
        info: strawberry.Info,
        id: int,
        email: Optional[str] = None,
        username: Optional[str] = None
    ) -> UserResponse:
        """Update user information"""
        db = info.context["db"]
        user = await db.update_user(id, email=email, username=username)
        return UserResponse(
            success=True,
            user=user,
            message="User updated successfully"
        )
```

## Query Examples

### Simple Query
```graphql
query {
  user(id: 1) {
    id
    email
    username
    isActive
  }
}
```

### Query with Variables
```graphql
query GetUser($userId: Int!) {
  user(id: $userId) {
    id
    email
    username
    createdAt
  }
}

# Variables
{
  "userId": 1
}
```

### Multiple Queries
```graphql
query {
  user(id: 1) {
    id
    email
  }
  users(limit: 5) {
    id
    username
  }
}
```

### Nested Queries
```graphql
query {
  user(id: 1) {
    id
    email
    notifications {
      id
      message
      isRead
      createdAt
    }
  }
}
```

## Mutation Examples

### Simple Mutation
```graphql
mutation {
  createUser(
    email: "user@example.com"
    username: "newuser"
    password: "securepassword"
  ) {
    success
    message
    user {
      id
      email
      username
    }
  }
}
```

### Mutation with Variables
```graphql
mutation CreateUser($email: String!, $username: String!, $password: String!) {
  createUser(email: $email, username: $username, password: $password) {
    success
    message
    user {
      id
      email
    }
  }
}

# Variables
{
  "email": "user@example.com",
  "username": "newuser",
  "password": "securepassword"
}
```

## Advanced Features

### Fragments
```graphql
fragment UserFields on User {
  id
  email
  username
  createdAt
}

query {
  user(id: 1) {
    ...UserFields
  }
  users(limit: 5) {
    ...UserFields
  }
}
```

### Aliases
```graphql
query {
  user1: user(id: 1) {
    email
  }
  user2: user(id: 2) {
    email
  }
}
```

### Directives
```graphql
query GetUser($includeNotifications: Boolean!) {
  user(id: 1) {
    id
    email
    notifications @include(if: $includeNotifications) {
      message
    }
  }
}
```

## Subscriptions (WebSocket)

For real-time updates, GraphQL subscriptions can be implemented:

```python
import strawberry
from typing import AsyncGenerator

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def notification_updates(
        self,
        info: strawberry.Info,
        user_id: int
    ) -> AsyncGenerator[Notification, None]:
        """Subscribe to notification updates"""
        # Implementation using WebSocket
        async for notification in notification_stream(user_id):
            yield notification
```

Usage:
```graphql
subscription {
  notificationUpdates(userId: 1) {
    id
    message
    isRead
  }
}
```

## Error Handling

### GraphQL Errors
```json
{
  "data": null,
  "errors": [
    {
      "message": "User not found",
      "locations": [{"line": 2, "column": 3}],
      "path": ["user"]
    }
  ]
}
```

### Custom Errors
```python
import strawberry

@strawberry.type
class Error:
    message: str
    code: str

@strawberry.type
class UserResult:
    user: Optional[User]
    errors: Optional[List[Error]]

# In resolver
if not user:
    return UserResult(
        user=None,
        errors=[Error(message="User not found", code="USER_NOT_FOUND")]
    )
```

## Performance Optimization

### DataLoader (N+1 Problem)

Prevent N+1 queries using DataLoader:

```python
from strawberry.dataloader import DataLoader

async def load_users(keys: List[int]) -> List[User]:
    """Batch load users by IDs"""
    users = await db.get_users_by_ids(keys)
    return users

# In context
user_loader = DataLoader(load_fn=load_users)

# In resolver
@strawberry.field
async def user(self, info: strawberry.Info, id: int) -> User:
    return await info.context["user_loader"].load(id)
```

### Query Complexity Limiting

```python
from strawberry.extensions import QueryDepthLimiter

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        QueryDepthLimiter(max_depth=10)
    ]
)
```

### Field-level Caching

```python
import strawberry
from functools import lru_cache

@strawberry.type
class Query:
    @strawberry.field
    @lru_cache(maxsize=100)
    async def expensive_query(self, info: strawberry.Info) -> str:
        # Expensive operation
        return result
```

## Testing GraphQL Queries

### Using pytest

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_query():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/graphql",
            json={
                "query": """
                    query {
                        user(id: 1) {
                            id
                            email
                        }
                    }
                """
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["user"]["id"] == 1
```

## Integration with REST API

GraphQL and REST can coexist:

```python
# REST endpoint
@router.get("/users/{user_id}")
async def get_user_rest(user_id: int):
    return await get_user(user_id)

# GraphQL query
@strawberry.field
async def user(self, info: strawberry.Info, id: int) -> User:
    return await get_user(id)
```

Clients can choose which API to use based on their needs:
- **REST**: Simple CRUD operations
- **GraphQL**: Complex queries, nested data, multiple resources

## Best Practices

1. **Use descriptive names** for queries and mutations
2. **Document your schema** with descriptions
3. **Version your schema** for breaking changes
4. **Implement proper authorization** at the field level
5. **Use DataLoader** to prevent N+1 queries
6. **Limit query depth** to prevent abuse
7. **Cache frequently accessed data**
8. **Monitor query performance**
9. **Use fragments** to avoid repetition
10. **Handle errors gracefully**

## Schema Documentation

GraphQL is self-documenting. Use the introspection query:

```graphql
query {
  __schema {
    types {
      name
      description
    }
  }
}
```

Or explore in GraphQL Playground with auto-complete and documentation sidebar.

## Resources

- [Strawberry GraphQL Documentation](https://strawberry.rocks/)
- [GraphQL Specification](https://spec.graphql.org/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
