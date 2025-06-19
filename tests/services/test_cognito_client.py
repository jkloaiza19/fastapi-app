# tests/services/test_cognito_client.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from jose import jwt
from jose.exceptions import JWTError
from schemas.login_schema import SignInRequest, SignUpRequest, RefreshTokenRequest
from services.aws.cognito import CognitoClient
from db.models import User

SECRET = "secret"
ALGO = "HS256"


@pytest.fixture
def mock_boto_client():
    client = MagicMock()
    client.sign_up.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    client.initiate_auth.return_value = {
        "AuthenticationResult": {
            "IdToken": "id_token",
            "AccessToken": "access_token",
            "RefreshToken": "refresh_token",
            "TokenType": "Bearer",
            "ExpiresIn": 3600
        }
    }
    client.get_user.return_value = {"Username": "testuser"}
    return client


@pytest.fixture
def mock_http_client():
    http = AsyncMock()
    http.get_request.return_value = {
        "keys": [{"kid": "abc", "kty": "RSA", "n": "n", "e": "AQAB"}]
    }
    return http


@pytest.fixture
def cognito_client(mock_boto_client, mock_http_client):
    mock_aws_client = MagicMock()
    mock_aws_client.get_client.return_value = mock_boto_client
    return CognitoClient(mock_aws_client, mock_http_client)


def test_sign_up_success(cognito_client):
    req = SignUpRequest(username="user", password="Password123!", email="user@test.com")
    assert cognito_client.sign_up(req) is True


def test_sign_in_success(cognito_client):
    req = SignInRequest(username="user", password="Password123!")
    res = cognito_client.sign_in(req)
    assert res["access_token"] == "access_token"


def test_refresh_token_success(cognito_client, mock_boto_client):
    mock_boto_client.initiate_auth.return_value = {
        "AuthenticationResult": {
            "IdToken": "id",
            "AccessToken": "access",
            "TokenType": "Bearer",
            "ExpiresIn": 3600
        }
    }
    data = RefreshTokenRequest(refresh_token="dummy_refresh_token")
    res = cognito_client.refresh_token(data)
    assert res["access_token"] == "access"


@pytest.mark.asyncio
async def test_get_cognito_public_keys(cognito_client):
    keys = await cognito_client.get_cognito_public_keys()
    assert "abc" in keys


@pytest.mark.asyncio
async def test_get_current_user_success(cognito_client, mock_boto_client):
    db = AsyncMock()
    redis = AsyncMock()
    db.find_unique.return_value = User(username="testuser")

    user = await cognito_client.get_current_user("token", db=db, redis=redis)
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_verify_token_valid(cognito_client, monkeypatch):
    db = AsyncMock()
    user = User(username="testuser")
    db.find_unique.return_value = user

    token = jwt.encode({"username": "testuser", "aud": "clientid", "iss": "issuer"}, SECRET, algorithm=ALGO)
    monkeypatch.setattr(jwt, "get_unverified_headers", lambda x: {"kid": "abc"})
    monkeypatch.setattr(cognito_client, "get_cognito_public_keys", AsyncMock(return_value={"abc": SECRET}))

    result = await cognito_client.verify_token(token, db=db)
    assert result["username"] == "testuser"


@pytest.mark.asyncio
async def test_verify_token_invalid_key(cognito_client, monkeypatch):
    db = AsyncMock()
    token = jwt.encode({"username": "testuser"}, SECRET, algorithm=ALGO)
    monkeypatch.setattr(jwt, "get_unverified_headers", lambda x: {"kid": "wrong"})
    monkeypatch.setattr(cognito_client, "get_cognito_public_keys", AsyncMock(return_value={"abc": SECRET}))

    with pytest.raises(HTTPException) as e:
        await cognito_client.verify_token(token, db=db)
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_malformed(cognito_client):
    db = AsyncMock()
    with pytest.raises(HTTPException) as e:
        await cognito_client.verify_token("invalid.token.structure", db=db)
    assert e.value.status_code == 401
