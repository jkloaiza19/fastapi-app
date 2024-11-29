from openai import OpenAI, APIError
from openai.types.chat import ChatCompletionMessage
from openai import APIError
from fastapi import HTTPException, status
from typing import AsyncGenerator
from core.logger import get_logger
from core.config import settings
from services.http.http_client import HttpClient
from services.AI.interfaces import OpenAIInterface

client = OpenAI(api_key=settings.OPENAI_API_KEY)

logger = get_logger(__name__)

chat_completion_role = "You are a helpful and friendly assistant."
chat_completion_http_url = f"{settings.OPENAI_HTTP_URL}/chat/completions"
headers = {
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
}


class ChatCompletion(OpenAIInterface):
    def __init__(self, http_client: HttpClient):
        self.http_client = http_client
        self.base_url = settings.OPENAI_HTTP_URL
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.CHAT_COMPLETION_MODEL
        self.temperature = 0
        self.system_role = "You are a helpful and friendly assistant."
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def get_model_response(self, prompt: str) -> dict:
        """Fetch chat completion response from OpenAI API."""
        try:
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_role},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.temperature,
            }

            result = await self.http_client.post_request(
                url=f"{self.base_url}/chat/completions",
                data=data,
                custom_headers=self.headers
            )

            return result["choices"][0]["message"]
        except APIError as e:
            logger.error(f"There was an error generating message: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"There was an error generating message: {str(e)}"
            )


def get_chat_completion_service() -> AsyncGenerator[OpenAIInterface, None]:
    try:
        http_client = HttpClient()
        chat_completion = ChatCompletion(
            http_client=http_client,
        )
        yield chat_completion
    except APIError as e:
        logger.error(str(e))
        raise e
    finally:
        chat_completion



def get_chat_completion(http_client: HttpClient) -> ChatCompletion:
    return ChatCompletion(http_client)


async def get_chat_completion(prompt: str) -> ChatCompletionMessage:
    try:
        logger.info(f"{prompt}")
        completion = client.chat.completions.create(
            model=settings.CHAT_COMPLETION_MODEL,
            messages=[
                {"role": "system", "content": chat_completion_role},
                {"role": "user", "content": prompt}
            ]
        )

        return completion.choices[0].message
    except APIError as e:
        logger.error(f"There was an error generating message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"There was an error generating message: {e}"
        )
