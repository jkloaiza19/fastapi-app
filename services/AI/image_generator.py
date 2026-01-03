from json import JSONDecodeError
from fastapi import HTTPException
from typing import AsyncGenerator

from openai import OpenAI
from abc import ABC, abstractmethod
from httpx import HTTPStatusError

from services.http.http_client import HttpClientInterface, HttpClientSingleton
from core.logger import get_logger
from core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = get_logger(__name__)

openai_image_url = "https://api.openai.com/v1/images/generations"
model = "dall-e-3"
size = "1024x1024"
quality = "standard"
n = 1


class ImageGeneratorInterface(ABC):
    @abstractmethod
    async def generate_image_from_text(self, prompt: str) -> dict:
        pass


class ImageGenerator(ImageGeneratorInterface):
    def __init__(self, http_client: HttpClientInterface):
        self.http_client = http_client
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_image_api = f"{settings.OPENAI_HTTP_URL}/images/generations"
        self.model = "dall-e-3"
        self.size = "1024x1024"

    async def generate_image_from_text(self, prompt: str) -> dict:
        try:
            response = await self.http_client.post_request(
                url=self.openai_image_api,
                data={
                    "model": self.model,
                    "prompt": prompt,
                    "size": self.size,
                    "quality": "standard",
                    "n": 1
                },
                custom_headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            )

            return {
                "url": response["data"][0]["url"],
                "revised_prompt": response["data"][0]["revised_prompt"]
            }
        except HTTPStatusError as e:
            logger.error(f"Error generating image from text: {str(e)}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
        except (JSONDecodeError, TypeError) as e:
            logger.error(f"Error decoding JSON response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e


async def get_image_generator_client() -> AsyncGenerator[ImageGeneratorInterface, None]:
    try:
        http_client = HttpClientSingleton().get_instance()
        image_generator = ImageGenerator(http_client=http_client)
        yield image_generator
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=f"Failed to initialize image generator service. {str(e)}")
