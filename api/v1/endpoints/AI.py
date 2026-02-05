from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Depends
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel, Field
from schemas.AI import (
    ChatCompletionRequest,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageEditRequest,
    ImageVariationRequest
)
from core.logger import get_logger
from api.dependencies import chat_completion_dep
from services.redis.redis_client import redis_dep
from services.AI.image_generator import get_image_generator_client, ImageGeneratorInterface
from utils.notion_loader import run_sync_threaded
from services.AI.rag.rag import retrieve, answer
from core.decorators.auth_decorator import api_key_required
from typing import Annotated, Optional
import json
import hashlib

logger = get_logger(__name__)
router = APIRouter()

class AskRequest(BaseModel):
    question: str = Field(min_length=1)


# @router.post("/chat-completion", status_code=200, response_model=ChatCompletionMessage)
# async def chat_completion(body: ChatCompletionRequest, http_client: http_client_dep):
#     return await get_chat_completion_http(http_client=http_client, prompt=body.prompt)

@router.post(
    "/chat-completion",
    status_code=200,
    response_model=ChatCompletionMessage,
    summary="Generate AI chat completion",
    description="""Generate an AI response using OpenAI's chat completion API.
    
    **Uses GPT models** (GPT-4, GPT-3.5-turbo, etc.) to generate intelligent responses
    based on the provided prompt.
    
    **Request body:**
    - `prompt`: The message or question to send to the AI
    
    **Returns:** AI-generated response message with:
    - `content`: The AI's text response
    - `role`: Message role (assistant)
    - Additional metadata from OpenAI
    
    **Use cases:**
    - Chatbots and conversational AI
    - Content generation
    - Question answering
    - Text analysis and summarization
    """,
)
async def chat_completion(body: ChatCompletionRequest, chat_completion_client: chat_completion_dep):
    return await chat_completion_client.get_model_response(prompt=body.prompt)

@router.post(
    "/run-sync",
    status_code=200,
    summary="Sync data from Notion",
    description="""Synchronize data from Notion workspace to the local database.
    
    **Authentication Required:** X-API-Key header
    
    This endpoint:
    - Fetches latest data from configured Notion databases
    - Processes and indexes content for RAG (Retrieval-Augmented Generation)
    - Updates the local knowledge base
    - Runs asynchronously in background thread
    
    **Use this** before running RAG queries to ensure up-to-date information.
    
    **Note:** This operation may take several seconds to minutes depending on
    the amount of data in your Notion workspace.
    """,
    responses={
        200: {"description": "Sync initiated successfully"},
        401: {"description": "X-API-Key header required"},
        403: {"description": "Invalid API key"}
    }
)
@api_key_required
async def run_sync_endpoint(request: Request):
    return await run_sync_threaded()

@router.post(
    "/rag/ask",
    summary="Ask a question using RAG",
    description="""Answer questions using Retrieval-Augmented Generation (RAG).
    
    **Authentication Required:** X-API-Key header
    
    **How it works:**
    1. Searches your indexed knowledge base (from Notion sync)
    2. Retrieves relevant document chunks
    3. Uses AI to generate accurate answers based on retrieved context
    
    **Features:**
    - Response caching for identical questions (improves performance)
    - Semantic search for better context matching
    - Source attribution in responses
    
    **Request body:**
    - `question`: Your question (minimum 1 character)
    
    **Returns:** Relevant documents and context that can answer your question.
    
    **Note:** Run `/run-sync` first to populate the knowledge base.
    """,
    responses={
        200: {"description": "Relevant documents retrieved"},
        401: {"description": "X-API-Key header required"},
        403: {"description": "Invalid API key"},
        404: {"description": "No relevant documents found. Run /run-sync to index data first."}
    }
)
@api_key_required
async def ask(req: AskRequest, request: Request, redis=redis_dep):
    cached = await redis.get_cached_data("ask", req.question)
    if cached:
        return cached

    docs = await retrieve(req.question)
    if not docs:
        raise HTTPException(404, "No relevant documents found. Ingest first.")
    
    return docs


@router.post("/images/generate", status_code=200, response_model=ImageGenerateResponse)
@api_key_required
async def generate_image(
    body: ImageGenerateRequest,
    request: Request,
    image_generator: ImageGeneratorInterface = Depends(get_image_generator_client),
    redis: redis_dep = None
):
    """
    Generate images from text prompts using DALL-E 2 or DALL-E 3.
    
    - **prompt**: Text description of the desired image (required)
    - **model**: dall-e-2 or dall-e-3 (default: dall-e-3)
    - **size**: Image dimensions (default: 1024x1024)
      - DALL-E 2: 256x256, 512x512, 1024x1024
      - DALL-E 3: 1024x1024, 1792x1024, 1024x1792
    - **quality**: standard or hd (DALL-E 3 only, default: standard)
    - **style**: vivid or natural (DALL-E 3 only, default: vivid)
    - **n**: Number of images (1 for DALL-E 3, 1-10 for DALL-E 2)
    - **response_format**: url or b64_json (default: url)
    """
    try:
        # Create cache key from request parameters
        hash_value = hashlib.md5(
            json.dumps({
                "prompt": body.prompt,
                "model": body.model,
                "size": body.size,
                "quality": body.quality,
                "style": body.style,
                "n": body.n
            }, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"image_gen:{hash_value}"
        
        # Check cache
        cached = await redis.get_cached_data(cache_key)
        if cached:
            logger.info("Returning cached image generation result")
            return cached

        # Generate image
        logger.info(f"Generating image with prompt: {body.prompt[:50]}...")
        result = await image_generator.generate_image(
            prompt=body.prompt,
            model=body.model,
            size=body.size,
            quality=body.quality,
            style=body.style,
            n=body.n,
            response_format=body.response_format
        )

        # Cache result for 24 hours
        await redis.set_cache_data(cache_key, result, ttl_sec=86400)
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate image: {str(e)}"
        )


@router.post("/images/edit", status_code=200, response_model=ImageGenerateResponse)
@api_key_required
async def edit_image(
    request: Request,
    image: UploadFile = File(..., description="PNG image file to edit (square, < 4MB)"),
    prompt: str = Form(..., description="Description of the desired edit"),
    mask: Optional[UploadFile] = File(None, description="Optional mask image (transparent areas indicate where to edit)"),
    size: str = Form("1024x1024", description="Output image size"),
    n: int = Form(1, ge=1, le=10, description="Number of edited images to generate"),
    image_generator: ImageGeneratorInterface = Depends(get_image_generator_client),
):
    """
    Edit an image using DALL-E 2. The image must be a square PNG less than 4MB.
    
    - **image**: PNG image file to edit (required)
    - **prompt**: Description of the desired edit (required)
    - **mask**: Optional mask PNG (transparent areas will be edited)
    - **size**: Output size - 256x256, 512x512, or 1024x1024 (default: 1024x1024)
    - **n**: Number of variations (1-10, default: 1)
    
    Note: DALL-E 3 does not support image editing. Only DALL-E 2 is available for this endpoint.
    """
    try:
        # Validate image type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file must be an image"
            )

        # Read image bytes
        image_bytes = await image.read()
        
        # Validate image size (4MB limit)
        if len(image_bytes) > 4 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image must be less than 4MB"
            )

        # Read mask if provided
        mask_bytes = None
        if mask:
            if not mask.content_type or not mask.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail="Mask file must be an image"
                )
            mask_bytes = await mask.read()
            if len(mask_bytes) > 4 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="Mask image must be less than 4MB"
                )

        logger.info(f"Editing image with prompt: {prompt[:50]}...")
        result = await image_generator.edit_image(
            image=image_bytes,
            prompt=prompt,
            mask=mask_bytes,
            size=size,
            n=n
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing image: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to edit image: {str(e)}"
        )


@router.post("/images/variation", status_code=200, response_model=ImageGenerateResponse)
@api_key_required
async def create_image_variation(
    request: Request,
    image: UploadFile = File(..., description="PNG image file (square, < 4MB)"),
    n: int = Form(1, ge=1, le=10, description="Number of variations to generate"),
    size: str = Form("1024x1024", description="Output image size"),
    image_generator: ImageGeneratorInterface = Depends(get_image_generator_client),
):
    """
    Create variations of an image using DALL-E 2.
    
    - **image**: PNG image file (required, must be square and < 4MB)
    - **n**: Number of variations (1-10, default: 1)
    - **size**: Output size - 256x256, 512x512, or 1024x1024 (default: 1024x1024)
    
    Note: DALL-E 3 does not support image variations. Only DALL-E 2 is available for this endpoint.
    """
    try:
        # Validate image type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file must be an image"
            )

        # Read image bytes
        image_bytes = await image.read()
        
        # Validate image size (4MB limit)
        if len(image_bytes) > 4 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image must be less than 4MB"
            )

        logger.info(f"Creating {n} image variation(s)...")
        result = await image_generator.create_variation(
            image=image_bytes,
            n=n,
            size=size
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating image variations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create image variations: {str(e)}"
        )
