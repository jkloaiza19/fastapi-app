from abc import ABC, abstractmethod
from openai.types.chat import ChatCompletionMessage


class OpenAIInterface(ABC):
    @abstractmethod
    async def get_model_response(self, prompt: str) -> ChatCompletionMessage:
        pass

