from __future__ import annotations

from typing import Optional, Literal
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse

from services.AI.ocr.ocr import OCRConfig, extract_text, extract_text_pdf

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff",
    "application/pdf",
}

# Supported document types
DocumentType = Literal["general", "passport"]

@router.post("/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Tesseract language codes (e.g., 'eng', 'spa', 'eng+spa')"),
    psm: int = Query(6, ge=0, le=13, description="Page Segmentation Mode"),
    oem: int = Query(3, ge=0, le=3, description="OCR Engine Mode"),
    grayscale: bool = Query(True, description="Convert to grayscale"),
    denoise: bool = Query(True, description="Apply denoising"),
    threshold: bool = Query(True, description="Apply thresholding"),
    resize_factor: float = Query(1.5, ge=0.5, le=4.0, description="Image resize factor"),
    return_boxes: bool = Query(False, description="Return bounding boxes for detected text"),
    return_pages: bool = Query(False, description="For PDFs, include per-page results"),
    pdf_zoom: float = Query(2.0, ge=1.0, le=4.0, description="Rendering scale for PDFs (higher = sharper)"),
    doc_type: DocumentType = Query("general", description="Document type: 'general' for any document, 'passport' for passport extraction")
):
    """
    Extract text from images or PDFs using OCR.
    
    Supported document types:
    - **general**: Standard OCR for any document
    - **passport**: Extracts structured passport data including MRZ parsing
    
    When doc_type='passport', response includes additional 'passport_data' field with:
    - passport_number, surname, given_names, nationality
    - date_of_birth, sex, date_of_expiry
    - mrz_line1, mrz_line2 (Machine Readable Zone)
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported content type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    cfg = OCRConfig(
        lang=lang, 
        psm=psm, 
        oem=oem,
        grayscale=grayscale, 
        denoise=denoise, 
        threshold=threshold,
        resize_factor=resize_factor, 
        return_boxes=return_boxes,
        doc_type=doc_type,
        gpu=False
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
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@router.post("/extract/passport")
async def ocr_extract_passport(
    file: UploadFile = File(...),
    lang: str = Query("eng", description="Language code (recommended: 'eng' for passports)"),
    return_boxes: bool = Query(False, description="Return bounding boxes"),
    pdf_zoom: float = Query(2.0, ge=1.0, le=4.0, description="PDF rendering scale"),
):
    """
    Dedicated endpoint for passport OCR with optimized settings.
    
    Returns structured passport data including:
    - Personal information (name, nationality, sex, DOB)
    - Document details (passport number, issue/expiry dates)
    - Machine Readable Zone (MRZ) data
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Optimized config for passports
    cfg = OCRConfig(
        lang=lang,
        psm=6,  # Uniform block of text
        oem=3,
        grayscale=True,
        denoise=True,
        threshold=True,
        resize_factor=2.0,  # Higher resolution for MRZ
        return_boxes=return_boxes,
        doc_type="passport",
        gpu=False
    )
    
    try:
        if file.content_type == "application/pdf":
            result = extract_text_pdf(data, cfg, zoom=pdf_zoom)
        else:
            result = extract_text(data, cfg)
        
        # Ensure passport_data exists in response
        if "passport_data" not in result or not result["passport_data"]:
            raise HTTPException(
                status_code=422,
                detail="Could not extract passport data. Please ensure image quality is good and passport is clearly visible."
            )
        
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Passport OCR failed: {str(e)}")