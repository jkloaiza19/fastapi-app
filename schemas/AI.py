from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Literal, List


class OpenAIPromptBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prompt: str = Field(min_length=1, max_length=4000, description="Text prompt for generation")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens for completion")


class ChatCompletionRequest(OpenAIPromptBase):
    pass


class ImageGenerateRequest(BaseModel):
    """Request schema for image generation"""
    model_config = ConfigDict(from_attributes=True)
    
    prompt: str = Field(
        min_length=1,
        max_length=4000,
        description="Text description of the desired image"
    )
    model: Literal["dall-e-2", "dall-e-3"] = Field(
        default="dall-e-3",
        description="Model to use for generation"
    )
    size: Literal[
        "256x256", "512x512", "1024x1024",  # DALL-E 2
        "1792x1024", "1024x1792"  # DALL-E 3
    ] = Field(
        default="1024x1024",
        description="Size of the generated image"
    )
    quality: Literal["standard", "hd"] = Field(
        default="standard",
        description="Image quality (DALL-E 3 only)"
    )
    style: Literal["vivid", "natural"] = Field(
        default="vivid",
        description="Image style (DALL-E 3 only)"
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of images to generate (1 for DALL-E 3, 1-10 for DALL-E 2)"
    )
    response_format: Literal["url", "b64_json"] = Field(
        default="url",
        description="Format of the response (URL or base64 JSON)"
    )

    @field_validator('n')
    @classmethod
    def validate_n_for_model(cls, v, info):
        model = info.data.get('model', 'dall-e-3')
        if model == 'dall-e-3' and v > 1:
            raise ValueError('DALL-E 3 only supports generating 1 image at a time')
        return v


class ImageEditRequest(BaseModel):
    """Request schema for image editing"""
    model_config = ConfigDict(from_attributes=True)
    
    prompt: str = Field(
        min_length=1,
        max_length=1000,
        description="Description of the desired edit"
    )
    size: Literal["256x256", "512x512", "1024x1024"] = Field(
        default="1024x1024",
        description="Size of the output image"
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of edited images to generate"
    )


class ImageVariationRequest(BaseModel):
    """Request schema for image variations"""
    model_config = ConfigDict(from_attributes=True)
    
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of variations to generate"
    )
    size: Literal["256x256", "512x512", "1024x1024"] = Field(
        default="1024x1024",
        description="Size of the output images"
    )


class ImageData(BaseModel):
    """Single generated image data"""
    url: Optional[str] = Field(None, description="URL of the generated image")
    b64_json: Optional[str] = Field(None, description="Base64 encoded image data")
    revised_prompt: Optional[str] = Field(None, description="Revised prompt used by DALL-E 3")


class ImageGenerateResponse(BaseModel):
    """Response schema for image generation"""
    created: int = Field(description="Unix timestamp of when images were created")
    images: List[ImageData] = Field(description="List of generated images")


class ImageGeneratorRequest(OpenAIPromptBase):
    """Deprecated: Use ImageGenerateRequest instead"""
    pass



