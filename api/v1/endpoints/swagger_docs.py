from fastapi import Depends, FastAPI, HTTPException, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials, APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi.openapi.docs import get_swagger_ui_html

security = HTTPBasic()
header_scheme = APIKeyHeader(name="x-key", auto_error=False)

router = APIRouter()


@router.get("/docs", include_in_schema=True)
async def get_documentation(credentials: HTTPBasicCredentials = Depends(security)):
    print("Received credentials:", credentials.username, credentials.password)
    if credentials.username != "someone" or credentials.password != "password":
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    else:
        return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")
