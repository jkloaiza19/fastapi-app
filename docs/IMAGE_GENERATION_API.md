# Image Generation API Documentation

## Overview

The Image Generation API provides comprehensive image creation and manipulation capabilities using OpenAI's DALL-E 2 and DALL-E 3 models.

## Features

- ✅ **Text-to-Image Generation** - Create images from text descriptions
- ✅ **Image Editing** - Edit existing images with text prompts (DALL-E 2)
- ✅ **Image Variations** - Create variations of existing images (DALL-E 2)
- ✅ **Multiple Models** - Support for both DALL-E 2 and DALL-E 3
- ✅ **Flexible Sizing** - Multiple output sizes depending on model
- ✅ **Quality Control** - Standard and HD quality options (DALL-E 3)
- ✅ **Style Control** - Vivid or natural styles (DALL-E 3)
- ✅ **Redis Caching** - Automatic caching of generated images to reduce costs
- ✅ **API Key Authentication** - Secure access with API key validation

## Endpoints

### 1. Generate Image from Text

**POST** `/api/v1/ai/images/generate`

Generate images from text descriptions using DALL-E.

#### Request Body

```json
{
  "prompt": "A serene lake surrounded by mountains at sunset",
  "model": "dall-e-3",
  "size": "1024x1024",
  "quality": "standard",
  "style": "vivid",
  "n": 1,
  "response_format": "url"
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Text description of the desired image (1-4000 chars) |
| `model` | string | No | "dall-e-3" | Model to use: "dall-e-2" or "dall-e-3" |
| `size` | string | No | "1024x1024" | Image dimensions (see sizes table below) |
| `quality` | string | No | "standard" | Quality: "standard" or "hd" (DALL-E 3 only) |
| `style` | string | No | "vivid" | Style: "vivid" or "natural" (DALL-E 3 only) |
| `n` | integer | No | 1 | Number of images (1 for DALL-E 3, 1-10 for DALL-E 2) |
| `response_format` | string | No | "url" | Response format: "url" or "b64_json" |

#### Supported Sizes

| Model | Supported Sizes |
|-------|----------------|
| DALL-E 2 | 256x256, 512x512, 1024x1024 |
| DALL-E 3 | 1024x1024, 1792x1024, 1024x1792 |

#### Response

```json
{
  "created": 1678901234,
  "images": [
    {
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/...",
      "revised_prompt": "A tranquil lake reflecting..."
    }
  ]
}
```

#### Example cURL

```bash
curl -X POST "http://localhost:8000/api/v1/ai/images/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "A futuristic city at night with neon lights",
    "model": "dall-e-3",
    "size": "1792x1024",
    "quality": "hd",
    "style": "vivid"
  }'
```

---

### 2. Edit Image

**POST** `/api/v1/ai/images/edit`

Edit an existing image using a text prompt. Only available with DALL-E 2.

#### Request (multipart/form-data)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | File | Yes | - | PNG image to edit (square, < 4MB) |
| `prompt` | string | Yes | - | Description of the desired edit |
| `mask` | File | No | - | Optional mask PNG (transparent areas = edit areas) |
| `size` | string | No | "1024x1024" | Output size: 256x256, 512x512, or 1024x1024 |
| `n` | integer | No | 1 | Number of edited images (1-10) |

#### Response

```json
{
  "created": 1678901234,
  "images": [
    {
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/..."
    }
  ]
}
```

#### Example cURL

```bash
curl -X POST "http://localhost:8000/api/v1/ai/images/edit" \
  -H "X-API-Key: your-api-key" \
  -F "image=@original.png" \
  -F "mask=@mask.png" \
  -F "prompt=Add a rainbow in the sky" \
  -F "size=1024x1024" \
  -F "n=2"
```

#### Image Requirements

- Format: PNG only
- Max size: 4MB
- Must be square (width = height)
- Mask (if provided): Same requirements as image, transparent areas indicate where to edit

---

### 3. Create Image Variation

**POST** `/api/v1/ai/images/variation`

Create variations of an existing image. Only available with DALL-E 2.

#### Request (multipart/form-data)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | File | Yes | - | PNG image (square, < 4MB) |
| `n` | integer | No | 1 | Number of variations (1-10) |
| `size` | string | No | "1024x1024" | Output size: 256x256, 512x512, or 1024x1024 |

#### Response

```json
{
  "created": 1678901234,
  "images": [
    {
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/..."
    },
    {
      "url": "https://oaidalleapiprodscus.blob.core.windows.net/..."
    }
  ]
}
```

#### Example cURL

```bash
curl -X POST "http://localhost:8000/api/v1/ai/images/variation" \
  -H "X-API-Key: your-api-key" \
  -F "image=@source.png" \
  -F "n=3" \
  -F "size=1024x1024"
```

---

## Authentication

All endpoints require API key authentication via the `X-API-Key` header:

```bash
-H "X-API-Key: your-api-key-here"
```

---

## Caching

Image generation requests are automatically cached in Redis for 24 hours to:
- Reduce API costs
- Improve response times for duplicate requests
- Prevent rate limiting

Cache keys are generated from request parameters (prompt, model, size, quality, style, n).

---

## Error Handling

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid parameters or file format |
| 401 | Unauthorized - Missing or invalid API key |
| 404 | Not Found - Endpoint doesn't exist |
| 413 | Payload Too Large - Image exceeds 4MB limit |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server-side error |

### Error Response Format

```json
{
  "detail": "DALL-E 3 only supports generating 1 image at a time"
}
```

### Model-Specific Errors

#### DALL-E 3 Limitations
- Cannot generate more than 1 image at a time (n=1 only)
- Only supports sizes: 1024x1024, 1792x1024, 1024x1792
- Does not support image editing or variations

#### DALL-E 2 Limitations
- Cannot use quality parameter
- Cannot use style parameter
- Only supports sizes: 256x256, 512x512, 1024x1024

---

## Best Practices

### 1. Prompt Engineering

**Good prompts:**
- Be specific and descriptive
- Include style, mood, and details
- Specify perspective and composition

**Example:**
```json
{
  "prompt": "A photorealistic portrait of a wise old wizard with a long white beard, wearing purple robes, standing in a library filled with ancient books, soft candlelight, fantasy art style"
}
```

### 2. Model Selection

**Use DALL-E 3 when:**
- You need the highest quality
- You want more prompt adherence
- You need wide/tall aspect ratios (1792x1024 or 1024x1792)

**Use DALL-E 2 when:**
- You need multiple images at once
- You want to edit or create variations of existing images
- Cost optimization is important (DALL-E 2 is cheaper)

### 3. Performance Optimization

- Use caching effectively by reusing prompts
- Request only the size you need
- Use standard quality unless HD is necessary
- Implement retry logic for transient errors

### 4. File Upload Best Practices

For edit/variation endpoints:
- Always use PNG format
- Ensure images are square before uploading
- Compress images to stay under 4MB
- Use transparent areas in masks to indicate edit regions

---

## Code Examples

### Python (using requests)

```python
import requests

# Generate image
url = "http://localhost:8000/api/v1/ai/images/generate"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key"
}
data = {
    "prompt": "A beautiful sunset over the ocean",
    "model": "dall-e-3",
    "size": "1024x1024",
    "quality": "hd",
    "style": "natural"
}

response = requests.post(url, json=data, headers=headers)
result = response.json()
image_url = result["images"][0]["url"]
print(f"Generated image: {image_url}")
```

### JavaScript (using fetch)

```javascript
// Generate image
const response = await fetch('http://localhost:8000/api/v1/ai/images/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify({
    prompt: 'A cyberpunk cityscape with flying cars',
    model: 'dall-e-3',
    size: '1792x1024',
    quality: 'hd',
    style: 'vivid'
  })
});

const result = await response.json();
console.log('Image URL:', result.images[0].url);
```

### Python (multipart file upload)

```python
import requests

# Create variation
url = "http://localhost:8000/api/v1/ai/images/variation"
headers = {"X-API-Key": "your-api-key"}

with open("source.png", "rb") as f:
    files = {"image": ("source.png", f, "image/png")}
    data = {
        "n": 3,
        "size": "1024x1024"
    }
    
    response = requests.post(url, files=files, data=data, headers=headers)
    result = response.json()
    
for i, img in enumerate(result["images"]):
    print(f"Variation {i+1}: {img['url']}")
```

---

## Rate Limits

OpenAI enforces rate limits on image generation:

| Model | Requests per minute |
|-------|---------------------|
| DALL-E 2 | 50 |
| DALL-E 3 | 7 (standard), 2 (HD) |

The API will return a 429 status code if rate limits are exceeded. Implement exponential backoff retry logic.

---

## Pricing Considerations

**DALL-E 3:**
- 1024x1024 standard: $0.040 per image
- 1024x1024 HD: $0.080 per image
- 1792x1024 / 1024x1792 standard: $0.080 per image
- 1792x1024 / 1024x1792 HD: $0.120 per image

**DALL-E 2:**
- 256x256: $0.016 per image
- 512x512: $0.018 per image
- 1024x1024: $0.020 per image

The caching layer helps reduce costs by avoiding duplicate API calls.

---

## Architecture

### Components

1. **Service Layer** (`services/AI/image_generator.py`)
   - `ImageGenerator` class implementing business logic
   - Validation, error handling, and API communication
   - Support for generate, edit, and variation operations

2. **Schemas** (`schemas/AI.py`)
   - `ImageGenerateRequest` - Text-to-image request
   - `ImageEditRequest` - Image editing request
   - `ImageVariationRequest` - Variation request
   - `ImageGenerateResponse` - Unified response schema

3. **Endpoints** (`api/v1/endpoints/AI.py`)
   - `/images/generate` - Text-to-image generation
   - `/images/edit` - Image editing
   - `/images/variation` - Image variations

4. **HTTP Client** (`services/http/http_client.py`)
   - Supports JSON and multipart/form-data requests
   - Automatic retry with exponential backoff
   - Connection pooling and timeout management

### Data Flow

```
Client Request
    ↓
API Endpoint (auth, validation)
    ↓
Redis Cache Check
    ↓ (cache miss)
Image Generator Service
    ↓
HTTP Client (retry logic)
    ↓
OpenAI API
    ↓
Response Processing
    ↓
Redis Cache Store
    ↓
Client Response
```

---

## Troubleshooting

### Issue: "Image must be square"
**Solution:** Resize your image to have equal width and height before uploading.

### Issue: "DALL-E 3 only supports generating 1 image at a time"
**Solution:** Set `n=1` when using DALL-E 3, or switch to DALL-E 2 for multiple images.

### Issue: "Image must be less than 4MB"
**Solution:** Compress your PNG file before uploading.

### Issue: "DALL-E 2 does not support quality parameter"
**Solution:** Remove `quality` parameter or set it to "standard" when using DALL-E 2.

### Issue: Rate limit exceeded
**Solution:** Implement exponential backoff or reduce request frequency.

---

## Future Enhancements

- [ ] Image-to-image translation
- [ ] Batch processing support
- [ ] Webhook notifications for long-running tasks
- [ ] Image storage integration (S3, Cloud Storage)
- [ ] User quota management
- [ ] Analytics and usage tracking
- [ ] Custom watermarking
- [ ] Image metadata extraction

---

## Support

For issues or questions:
- Check the error response for specific details
- Review the logs for detailed error traces
- Consult OpenAI's DALL-E documentation for model-specific limitations

---

## Changelog

### v1.0.0 (Current)
- ✅ Initial release with DALL-E 2 and DALL-E 3 support
- ✅ Text-to-image generation
- ✅ Image editing (DALL-E 2)
- ✅ Image variations (DALL-E 2)
- ✅ Multiple sizes and quality options
- ✅ Redis caching
- ✅ Comprehensive error handling
- ✅ API key authentication
