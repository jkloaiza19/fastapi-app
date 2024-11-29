from fastapi import APIRouter
from openai.types.chat import ChatCompletionMessage
from schemas.AI import ChatCompletionRequest
from core.logger import get_logger
from api.dependencies import chat_completion_dep

logger = get_logger(__name__)
router = APIRouter()


# @router.post("/chat-completion", status_code=200, response_model=ChatCompletionMessage)
# async def chat_completion(body: ChatCompletionRequest, http_client: http_client_dep):
#     return await get_chat_completion_http(http_client=http_client, prompt=body.prompt)

@router.post("/chat-completion", status_code=200, response_model=ChatCompletionMessage)
async def chat_completion(body: ChatCompletionRequest, chat_completion_client: chat_completion_dep):
    return await chat_completion_client.get_model_response(prompt=body.prompt)
