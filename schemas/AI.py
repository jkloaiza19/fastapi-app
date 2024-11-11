from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class OpenAIPromptBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prompt: str = Field(max_length=255)
    max_tokens: Optional[int] = Field(default=None)


class ImageGeneratorRequest(OpenAIPromptBase):
    pass


class ChatCompletionRequest(OpenAIPromptBase):
    pass



