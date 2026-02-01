from json import JSONDecodeError
from fastapi import HTTPException
from typing import AsyncGenerator, Optional, Literal
from enum import Enum
import base64
import io

from openai import OpenAI
from abc import ABC, abstractmethod
from httpx import HTTPStatusError

from services.http.http_client import HttpClientInterface, HttpClientSingleton
from core.logger import get_logger
from core.config import settings


logger = get_logger(__name__)


class ImageModel(str, Enum):
    """Supported image generation models"""
    DALL_E_3 = "dall-e-3"
    DALL_E_2 = "dall-e-2"


class ImageSize(str, Enum):
    """Supported image sizes"""
    SIZE_256 = "256x256"  # DALL-E 2 only
    SIZE_512 = "512x512"  # DALL-E 2 only
    SIZE_1024 = "1024x1024"  # Both
    SIZE_1792_1024 = "1792x1024"  # DALL-E 3 only
    SIZE_1024_1792 = "1024x1792"  # DALL-E 3 only


class ImageQuality(str, Enum):
    """Image quality levels (DALL-E 3 only)"""
    STANDARD = "standard"
    HD = "hd"


class ImageStyle(str, Enum):
    """Image style (DALL-E 3 only)"""
    VIVID = "vivid"
    NATURAL = "natural"


class ImageFormat(str, Enum):
    """Response format for generated images"""
    URL = "url"
    B64_JSON = "b64_json"


class ImageGeneratorInterface(ABC):
    @abstractmethod
    async def generate_image(self, 
                            prompt: str, 
                            model: str = ImageModel.DALL_E_3,
                            size: str = ImageSize.SIZE_1024,
                            quality: str = ImageQuality.STANDARD,
                            style: str = ImageStyle.VIVID,
                            n: int = 1,
                            response_format: str = ImageFormat.URL) -> dict:
        pass

    @abstractmethod
    async def edit_image(self,
                        image: bytes,
                        prompt: str,
                        mask: Optional[bytes] = None,
                        size: str = ImageSize.SIZE_1024,
                        n: int = 1) -> dict:
        pass

    @abstractmethod
    async def create_variation(self,
                              image: bytes,
                              n: int = 1,
                              size: str = ImageSize.SIZE_1024) -> dict:
        pass


class ImageGenerator(ImageGeneratorInterface):
    """OpenAI Image Generation Service with DALL-E 2 and DALL-E 3 support"""
    
    def __init__(self, http_client: HttpClientInterface):
        self.http_client = http_client
        self.openai_image_api = f"{settings.OPENAI_HTTP_URL}/images/generations"
        self.openai_edit_api = f"{settings.OPENAI_HTTP_URL}/images/edits"
        self.openai_variation_api = f"{settings.OPENAI_HTTP_URL}/images/variations"
        self.api_key = settings.OPENAI_API_KEY
        self._headers = {"Authorization": f"Bearer {self.api_key}"}

    def _validate_model_params(self, model: str, size: str, quality: str, style: str) -> None:
        """Validate parameters based on model capabilities"""
        if model == ImageModel.DALL_E_2:
            if size not in [ImageSize.SIZE_256, ImageSize.SIZE_512, ImageSize.SIZE_1024]:
                raise HTTPException(
                    status_code=400,
                    detail=f"DALL-E 2 only supports sizes: 256x256, 512x512, 1024x1024"
                )
            if quality != ImageQuality.STANDARD:
                raise HTTPException(
                    status_code=400,
                    detail="DALL-E 2 does not support quality parameter"
                )
            if style != ImageStyle.VIVID:
                raise HTTPException(
                    status_code=400,
                    detail="DALL-E 2 does not support style parameter"
                )
        elif model == ImageModel.DALL_E_3:
            if size not in [ImageSize.SIZE_1024, ImageSize.SIZE_1792_1024, ImageSize.SIZE_1024_1792]:
                raise HTTPException(
                    status_code=400,
                    detail=f"DALL-E 3 only supports sizes: 1024x1024, 1792x1024, 1024x1792"
                )

    async def generate_image(self,
                            prompt: str,
                            model: str = ImageModel.DALL_E_3,
                            size: str = ImageSize.SIZE_1024,
                            quality: str = ImageQuality.STANDARD,
                            style: str = ImageStyle.VIVID,
                            n: int = 1,
                            response_format: str = ImageFormat.URL) -> dict:
        """
        Generate images from text prompts using DALL-E.
        
        Args:
            prompt: Text description of the desired image
            model: Model to use (dall-e-2 or dall-e-3)
            size: Image dimensions
            quality: Image quality (standard or hd) - DALL-E 3 only
            style: Image style (vivid or natural) - DALL-E 3 only
            n: Number of images to generate (1-10 for DALL-E 2, 1 for DALL-E 3)
            response_format: url or b64_json
            
        Returns:
            dict with generated image data
        """
        try:
            # Validate parameters
            self._validate_model_params(model, size, quality, style)
            
            if model == ImageModel.DALL_E_3 and n > 1:
                raise HTTPException(
                    status_code=400,
                    detail="DALL-E 3 only supports generating 1 image at a time"
                )
            
            if not (1 <= n <= 10):
                raise HTTPException(
                    status_code=400,
                    detail="Number of images must be between 1 and 10"
                )

            # Build request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "n": n,
                "response_format": response_format
            }
            
            # Add DALL-E 3 specific parameters
            if model == ImageModel.DALL_E_3:
                payload["quality"] = quality
                payload["style"] = style

            logger.info(f"Generating image with model={model}, size={size}, n={n}")
            
            response = await self.http_client.post_request(
                url=self.openai_image_api,
                data=payload,
                custom_headers=self._headers
            )

            # Format response
            result = {
                "created": response.get("created"),
                "images": []
            }
            
            for img_data in response["data"]:
                image_info = {}
                if response_format == ImageFormat.URL:
                    image_info["url"] = img_data["url"]
                else:
                    image_info["b64_json"] = img_data["b64_json"]
                
                # DALL-E 3 returns revised prompt
                if "revised_prompt" in img_data:
                    image_info["revised_prompt"] = img_data["revised_prompt"]
                
                result["images"].append(image_info)

            logger.info(f"Successfully generated {len(result['images'])} image(s)")
            return result
            
        except HTTPStatusError as e:
            error_detail = str(e)
            try:
                error_detail = e.response.json().get("error", {}).get("message", str(e))
            except:
                pass
            logger.error(f"Error generating image: {error_detail}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"OpenAI API error: {error_detail}"
            ) from e
        except (JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error processing response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process image generation response: {str(e)}"
            ) from e
        except ValueError as e:
            logger.error(f"Invalid parameter: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    async def edit_image(self,
                        image: bytes,
                        prompt: str,
                        mask: Optional[bytes] = None,
                        size: str = ImageSize.SIZE_1024,
                        n: int = 1) -> dict:
        """
        Edit an image using DALL-E 2 (DALL-E 3 does not support edits).
        
        Args:
            image: PNG image file (must be square and < 4MB)
            prompt: Description of the desired edit
            mask: Optional mask image (transparent areas indicate where to edit)
            size: Output image size
            n: Number of variations (1-10)
            
        Returns:
            dict with edited image URLs
        """
        try:
            if not (1 <= n <= 10):
                raise HTTPException(
                    status_code=400,
                    detail="Number of images must be between 1 and 10"
                )

            # Prepare multipart form data
            files = {
                "image": ("image.png", image, "image/png"),
                "prompt": (None, prompt),
                "n": (None, str(n)),
                "size": (None, size)
            }
            
            if mask:
                files["mask"] = ("mask.png", mask, "image/png")

            logger.info(f"Editing image with n={n}, size={size}")
            
            # Note: This requires a different HTTP client method for multipart/form-data
            # You may need to implement this in your http_client
            response = await self.http_client.post_multipart(
                url=self.openai_edit_api,
                files=files,
                custom_headers=self._headers
            )

            result = {
                "created": response.get("created"),
                "images": [{"url": img["url"]} for img in response["data"]]
            }

            logger.info(f"Successfully edited image with {len(result['images'])} variation(s)")
            return result
            
        except HTTPStatusError as e:
            error_detail = str(e)
            try:
                error_detail = e.response.json().get("error", {}).get("message", str(e))
            except:
                pass
            logger.error(f"Error editing image: {error_detail}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"OpenAI API error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Error editing image: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to edit image: {str(e)}"
            ) from e

    async def create_variation(self,
                              image: bytes,
                              n: int = 1,
                              size: str = ImageSize.SIZE_1024) -> dict:
        """
        Create variations of an image using DALL-E 2.
        
        Args:
            image: PNG image file (must be square and < 4MB)
            n: Number of variations (1-10)
            size: Output image size
            
        Returns:
            dict with variation image URLs
        """
        try:
            if not (1 <= n <= 10):
                raise HTTPException(
                    status_code=400,
                    detail="Number of images must be between 1 and 10"
                )

            files = {
                "image": ("image.png", image, "image/png"),
                "n": (None, str(n)),
                "size": (None, size)
            }

            logger.info(f"Creating {n} image variation(s) with size={size}")
            
            response = await self.http_client.post_multipart(
                url=self.openai_variation_api,
                files=files,
                custom_headers=self._headers
            )

            result = {
                "created": response.get("created"),
                "images": [{"url": img["url"]} for img in response["data"]]
            }

            logger.info(f"Successfully created {len(result['images'])} variation(s)")
            return result
            
        except HTTPStatusError as e:
            error_detail = str(e)
            try:
                error_detail = e.response.json().get("error", {}).get("message", str(e))
            except:
                pass
            logger.error(f"Error creating variations: {error_detail}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"OpenAI API error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Error creating variations: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create variations: {str(e)}"
            ) from e


async def get_image_generator_client() -> AsyncGenerator[ImageGeneratorInterface, None]:
    """Dependency injection for image generator service"""
    try:
        http_client = HttpClientSingleton().get_instance()
        image_generator = ImageGenerator(http_client=http_client)
        yield image_generator
    except Exception as e:
        logger.error(f"Failed to initialize image generator: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize image generator service: {str(e)}"
        )
