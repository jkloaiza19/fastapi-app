from fastapi import APIRouter, HTTPException, Request
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, Field
from schemas.AI import ChatCompletionRequest
from core.logger import get_logger
from api.dependencies import chat_completion_dep
from services.redis.redis_client import redis_dep
from utils.notion_loader import run_sync_threaded
from services.AI.rag.rag import retrieve, answer
from core.decorators.auth_decorator import api_key_required

logger = get_logger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(min_length=1)


# @router.post("/chat-completion", status_code=200, response_model=ChatCompletionMessage)
# async def chat_completion(body: ChatCompletionRequest, http_client: http_client_dep):
#     return await get_chat_completion_http(http_client=http_client, prompt=body.prompt)

@router.post("/chat-completion", status_code=200, response_model=ChatCompletionMessage)
async def chat_completion(body: ChatCompletionRequest, chat_completion_client: chat_completion_dep):
    return await chat_completion_client.get_model_response(prompt=body.prompt)

@router.post("/run-sync", status_code=200)
@api_key_required
async def run_sync_endpoint(request: Request):
    return await run_sync_threaded()

@router.post("/rag/ask")
@api_key_required
async def ask(req: AskRequest, request: Request, redis=redis_dep):
    cached = await redis.get_cached_data("ask", req.question)
    if cached:
        return cached

    docs = await retrieve(req.question)
    if not docs:
        raise HTTPException(404, "No relevant documents found. Ingest first.")
    
    return docs
