from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from services.AI.ocr.ocr import OCRConfig, extract_text, extract_text_pdf

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff",
    "application/pdf",
}

@router.post("/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Tesseract language codes (e.g., 'eng', 'spa', 'eng+spa')"),
    psm: int = Query(6, ge=0, le=13),
    oem: int = Query(3, ge=0, le=3),
    grayscale: bool = Query(True),
    denoise: bool = Query(True),
    threshold: bool = Query(True),
    resize_factor: float = Query(1.5, ge=0.5, le=4.0),
    return_boxes: bool = Query(False),
    return_pages: bool = Query(False, description="For PDFs, include per-page results"),
    pdf_zoom: float = Query(2.0, ge=1.0, le=4.0, description="Rendering scale for PDFs (higher = sharper)"),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    cfg = OCRConfig(
        lang=lang, psm=psm, oem=oem,
        grayscale=grayscale, denoise=denoise, threshold=threshold,
        resize_factor=resize_factor, return_boxes=return_boxes,
    )
    try:
        if file.content_type == "application/pdf":
            result = extract_text_pdf(data, cfg, zoom=pdf_zoom)
            if not return_pages:
                result.pop("pages", None)
            return JSONResponse(result)
        else:
            result = extract_text(data, cfg)
            return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")
