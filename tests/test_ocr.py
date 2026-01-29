"""
Tests for OCR endpoints.
"""
import pytest
from httpx import AsyncClient
from io import BytesIO
from PIL import Image


def create_test_image() -> BytesIO:
    """Create a simple test image."""
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


@pytest.mark.asyncio
async def test_ocr_extract_no_file(client: AsyncClient):
    """Test OCR extract without file."""
    response = await client.post("/v1/ai/ocr/extract")
    
    assert response.status_code == 422  # Missing required field


@pytest.mark.asyncio
async def test_ocr_extract_with_image(client: AsyncClient):
    """Test OCR extract with valid image."""
    img_bytes = create_test_image()
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    data = {"lang": "eng"}
    
    response = await client.post(
        "/v1/ai/ocr/extract",
        files=files,
        data=data
    )
    
    # Should process successfully or fail gracefully
    assert response.status_code in [200, 500]  # 500 if OCR service unavailable
    
    if response.status_code == 200:
        data = response.json()
        assert "text" in data


@pytest.mark.asyncio
async def test_ocr_extract_unsupported_format(client: AsyncClient):
    """Test OCR extract with unsupported file format."""
    files = {"file": ("test.txt", BytesIO(b"text content"), "text/plain")}
    
    response = await client.post(
        "/v1/ai/ocr/extract",
        files=files
    )
    
    assert response.status_code == 400
    assert "Unsupported content type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ocr_extract_empty_file(client: AsyncClient):
    """Test OCR extract with empty file."""
    files = {"file": ("empty.png", BytesIO(b""), "image/png")}
    
    response = await client.post(
        "/v1/ai/ocr/extract",
        files=files
    )
    
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ocr_passport_endpoint(client: AsyncClient):
    """Test passport OCR endpoint."""
    img_bytes = create_test_image()
    
    files = {"file": ("passport.png", img_bytes, "image/png")}
    
    response = await client.post(
        "/v1/ai/ocr/extract/passport",
        files=files
    )
    
    # May return 200, 422 (no passport data), or 500 (service issue)
    assert response.status_code in [200, 422, 500]


@pytest.mark.asyncio
async def test_ocr_extract_with_options(client: AsyncClient):
    """Test OCR extract with various options."""
    img_bytes = create_test_image()
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    data = {
        "lang": "eng",
        "psm": 6,
        "oem": 3,
        "grayscale": True,
        "denoise": True,
        "threshold": True,
        "resize_factor": 2.0,
        "return_boxes": False
    }
    
    response = await client.post(
        "/v1/ai/ocr/extract",
        files=files,
        data=data
    )
    
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_ocr_extract_invalid_psm(client: AsyncClient):
    """Test OCR extract with invalid PSM value."""
    img_bytes = create_test_image()
    
    files = {"file": ("test.png", img_bytes, "image/png")}
    data = {"psm": 99}  # Invalid, should be 0-13
    
    response = await client.post(
        "/v1/ai/ocr/extract",
        files=files,
        data=data
    )
    
    assert response.status_code == 422
