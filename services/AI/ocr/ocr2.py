from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import io
import ssl
import certifi

import numpy as np
from PIL import Image
import cv2
import fitz
import re
import easyocr
from .parsers2 import PassportData, extract_by_labels, parse_mrz_td3, normalize_ocr, find_mrz_lines, extract_passport_from_ocr

# Configure SSL to use certifi's certificates (fixes macOS SSL issues)
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())


@dataclass
class OCRConfig:
    lang: str = "eng"
    grayscale: bool = True
    denoise: bool = True
    threshold: bool = True
    resize_factor: float = 1.5
    return_boxes: bool = False
    doc_type: Optional[str] = None
    gpu: bool = False  # Use GPU acceleration if available
    psm: int = 3  # Page segmentation mode (Tesseract style)
    oem: int = 3  # OCR Engine mode (Tesseract style)


# @dataclass
# class PassportData:
#     """Structured passport data"""
#     passport_number: Optional[str] = None
#     surname: Optional[str] = None
#     given_names: Optional[str] = None
#     nationality: Optional[str] = None
#     date_of_birth: Optional[str] = None
#     sex: Optional[str] = None
#     place_of_birth: Optional[str] = None
#     date_of_issue: Optional[str] = None
#     date_of_expiry: Optional[str] = None
#     issuing_authority: Optional[str] = None
#     country_code: Optional[str] = None
#     mrz_line1: Optional[str] = None
#     mrz_line2: Optional[str] = None
    
    # def to_dict(self) -> dict:
    #     return {k: v for k, v in self.__dict__.items() if v is not None}


# Global reader cache to avoid reloading model
_reader_cache = {}


def _get_reader(langs: List[str], gpu: bool = False) -> easyocr.Reader:
    """Get or create EasyOCR reader instance (cached)"""
    cache_key = (tuple(sorted(langs)), gpu)
    if cache_key not in _reader_cache:
        _reader_cache[cache_key] = easyocr.Reader(langs, gpu=gpu, verbose=False)
    return _reader_cache[cache_key]


def _map_language_codes(tesseract_lang: str) -> List[str]:
    """Map Tesseract language codes to EasyOCR codes"""
    lang_map = {
        'eng': 'en',
        'spa': 'es',
        'fra': 'fr',
        'deu': 'de',
        'por': 'pt',
        'ita': 'it',
        'rus': 'ru',
        'jpn': 'ja',
        'kor': 'ko',
        'chi_sim': 'ch_sim',
        'chi_tra': 'ch_tra',
        'ara': 'ar',
        'hin': 'hi',
    }
    
    langs = []
    for lang in tesseract_lang.split('+'):
        langs.append(lang_map.get(lang, lang))
    
    return langs


def _load_image(bytes_data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(bytes_data)).convert("RGB")


def _preprocess(img: Image.Image, cfg: OCRConfig) -> np.ndarray:
    """Enhanced preprocessing for better OCR results"""
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # For passports, use higher resolution
    resize_factor = cfg.resize_factor
    if cfg.doc_type == "passport":
        resize_factor = max(resize_factor, 2.5)

    if resize_factor and resize_factor > 1.0:
        h, w = cv.shape[:2]
        cv = cv2.resize(cv, (int(w * resize_factor), int(h * resize_factor)), 
                       interpolation=cv2.INTER_CUBIC)

    if cfg.grayscale:
        cv = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)

    if cfg.denoise:
        if len(cv.shape) == 2:
            # Bilateral filter preserves edges
            cv = cv2.bilateralFilter(cv, 9, 75, 75)
            # Additional denoising
            cv = cv2.fastNlMeansDenoising(cv, None, h=10, templateWindowSize=7, searchWindowSize=21)

    if cfg.threshold:
        if len(cv.shape) == 2:
            # Adaptive threshold for better results with varying lighting
            cv = cv2.adaptiveThreshold(cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
    
    # Morphological operations for passport MRZ
    if cfg.doc_type == "passport" and len(cv.shape) == 2:
        kernel = np.ones((1, 1), np.uint8)
        cv = cv2.morphologyEx(cv, cv2.MORPH_CLOSE, kernel)
        cv = cv2.morphologyEx(cv, cv2.MORPH_OPEN, kernel)

    return cv


def _clean_text(text: str) -> str:
    """Clean OCR artifacts from text"""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[|+~_]', '', text)
    return text.strip()


def _extract_passport_data(text: str) -> PassportData:
    return extract_passport_from_ocr(text)
    # t = normalize_ocr(text)
    # mrz = find_mrz_lines(t)

    # # If we can find 2 MRZ lines, prefer that
    # # Often TD3 passports have exactly 2 lines; sometimes OCR splits them oddly.
    # if len(mrz) >= 2:
    #     # choose the last two candidates (often MRZ appears at bottom)
    #     info = parse_mrz_td3(mrz[-2], mrz[-1])
    #     return info

    # # If only line1 is present, at least parse names/issuer from it
    # if len(mrz) == 1:
    #     line1 = mrz[0]
    #     # Very rough: parse doc_type/issuer/names from line1
    #     # (still useful, but missing passport number/dates)
    #     dummy_line2 = "<"*44
    #     info = parse_mrz_td3(line1, dummy_line2)
    #     # then enrich from labels if possible
    #     fallback = extract_by_labels(t)
    #     for k, v in fallback.__dict__.items():
    #         if getattr(info, k) in (None, "", "0") and v:
    #             setattr(info, k, v)
    #     return info

    # # Else labels-only
    # return extract_by_labels(t)

    # """Extract structured data from passport OCR text"""
    # data = PassportData()
    
    # text = _clean_text(text)
    # lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # # Find MRZ lines (Machine Readable Zone)
    # mrz_pattern = r'^[A-Z0-9<]{40,44}$'
    # mrz_lines = []
    
    # for line in lines:
    #     cleaned_line = line.replace(' ', '').replace('|', 'I').replace('1', 'I').replace('0', 'O')
    #     if re.match(mrz_pattern, cleaned_line) and len(cleaned_line) >= 40:
    #         mrz_lines.append(cleaned_line)
    
    # # Process MRZ if found
    # if len(mrz_lines) >= 2:
    #     data.mrz_line1 = mrz_lines[-2][:44]
    #     data.mrz_line2 = mrz_lines[-1][:44]
        
    #     # Parse MRZ Line 1: P<COUNTRY_CODE<SURNAME<<GIVEN_NAMES
    #     mrz1 = data.mrz_line1
    #     if mrz1.startswith('P<'):
    #         data.country_code = mrz1[2:5].replace('<', '').strip()
    #         names_section = mrz1[5:44]
    #         parts = names_section.split('<<')
    #         if len(parts) >= 1:
    #             data.surname = parts[0].replace('<', ' ').strip()
    #         if len(parts) >= 2:
    #             data.given_names = parts[1].replace('<', ' ').strip()
        
    #     # Parse MRZ Line 2
    #     mrz2 = data.mrz_line2
    #     if len(mrz2) >= 44:
    #         data.passport_number = mrz2[:9].replace('<', '').strip()
    #         data.nationality = mrz2[10:13].replace('<', '').strip()
            
    #         dob = mrz2[13:19]
    #         if dob[:6].isdigit():
    #             yy, mm, dd = dob[:2], dob[2:4], dob[4:6]
    #             year = f"19{yy}" if int(yy) > 50 else f"20{yy}"
    #             data.date_of_birth = f"{year}-{mm}-{dd}"
            
    #         if mrz2[20] in ['M', 'F', 'X']:
    #             data.sex = mrz2[20]
            
    #         expiry = mrz2[21:27]
    #         if expiry[:6].isdigit():
    #             yy, mm, dd = expiry[:2], expiry[2:4], expiry[4:6]
    #             data.date_of_expiry = f"20{yy}-{mm}-{dd}"
    
    # # Fallback: Extract from text patterns
    # text_upper = text.upper()
    
    # if not data.country_code:
    #     if 'UNITED STATES' in text_upper or 'USA' in text_upper:
    #         data.country_code = 'USA'
    #         data.nationality = 'USA'
    
    # if not data.passport_number:
    #     passport_patterns = [
    #         r'(?:PASSPORT\s+(?:CARD|NO|NUMBER)?[\s:]*)?([A-Z0-9]{6,12})',
    #         r'No[\s.:]+([A-Z0-9]{6,12})',
    #     ]
    #     for pattern in passport_patterns:
    #         match = re.search(pattern, text_upper)
    #         if match:
    #             candidate = match.group(1)
    #             if not re.match(r'^(PASSPORT|CARD|USA|STATES|AMERICA)$', candidate):
    #                 data.passport_number = candidate
    #                 break
    
    # if not data.surname:
    #     surname_patterns = [
    #         r'(?:Surname|Last\s+Name|Sur)[\s:]+([A-Z][A-Z\s]+?)(?:\s+Given|\s+\d|\s*$)',
    #         r'^([A-Z]{2,})\s+[A-Z][a-z]+',
    #     ]
    #     for pattern in surname_patterns:
    #         match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    #         if match:
    #             surname = match.group(1).strip()
    #             if len(surname) > 1 and not re.match(r'^(PASSPORT|UNITED|STATES)$', surname.upper()):
    #                 data.surname = surname
    #                 break
    
    # if not data.given_names:
    #     given_patterns = [
    #         r'(?:Given\s+Names?|First\s+Name)[\s:]+([A-Z][A-Za-z\s]+?)(?:\s+Sex|\s+Date|\s+Place|\s*$)',
    #         r'Names?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    #     ]
    #     for pattern in given_patterns:
    #         match = re.search(pattern, text, re.IGNORECASE)
    #         if match:
    #             names = match.group(1).strip()
    #             if len(names) > 1:
    #                 data.given_names = names
    #                 break
    
    # if not data.date_of_birth:
    #     dob_patterns = [
    #         r'(?:Date\s+of\s+Birth|Birth|DOB)[\s:]+(\d{1,2}\s+[A-Z]{3}\s+\d{4})',
    #         r'(?:Date\s+of\s+Birth|Birth|DOB)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    #     ]
    #     for pattern in dob_patterns:
    #         match = re.search(pattern, text, re.IGNORECASE)
    #         if match:
    #             dob_str = match.group(1)
    #             if re.match(r'\d{1,2}\s+[A-Z]{3}\s+\d{4}', dob_str.upper()):
    #                 data.date_of_birth = dob_str
    #             break
    
    # if not data.sex:
    #     sex_patterns = [
    #         r'(?:Sex|Gender)[\s:]+([MFX])',
    #         r'\b([MF])\b(?=\s+\d{1,2}\s+[A-Z]{3})',
    #     ]
    #     for pattern in sex_patterns:
    #         match = re.search(pattern, text_upper)
    #         if match:
    #             data.sex = match.group(1)
    #             break
    
    # if not data.place_of_birth:
    #     pob_match = re.search(r'(?:Place\s+of\s+Birth)[\s:]+([A-Z][A-Za-z\s,\.]+?)(?:\s+Date|\s+Sex|\s*$)', text, re.IGNORECASE)
    #     if pob_match:
    #         data.place_of_birth = pob_match.group(1).strip()
    
    # if not data.issuing_authority:
    #     auth_match = re.search(r'(DEPARTMENT\s+OF\s+STATE|ISSUING\s+AUTHORITY)[^\n]*', text_upper)
    #     if auth_match:
    #         data.issuing_authority = auth_match.group(0).strip()
    
    # return data


def extract_text(image_bytes: bytes, cfg: Optional[OCRConfig] = None) -> dict:
    """
    Extract text from image using EasyOCR
    
    Returns:
      {
        "text": "...",
        "avg_conf": float | None,
        "boxes": [...] (if cfg.return_boxes),
        "passport_data": {...} (if cfg.doc_type == "passport")
      }
    """
    cfg = cfg or OCRConfig()
    pil = _load_image(image_bytes)
    proc = _preprocess(pil, cfg)
    
    # Get language codes
    langs = _map_language_codes(cfg.lang)
    reader = _get_reader(langs, cfg.gpu)
    
    result = {
        "text": "",
        "avg_conf": None,
        "boxes": [],
    }
    
    # Run EasyOCR
    # readtext returns: [(bbox, text, confidence), ...]
    detections = reader.readtext(proc, detail=1, paragraph=False)
    
    if not detections:
        return result
    
    texts: List[str] = []
    confs: List[float] = []
    boxes: List[dict] = []
    
    for (bbox, text, conf) in detections:
        texts.append(text)
        confs.append(conf * 100)  # Convert to percentage
        
        # Convert bbox format: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] -> [x, y, w, h]
        x_coords = [p[0] for p in bbox]
        y_coords = [p[1] for p in bbox]
        x, y = int(min(x_coords)), int(min(y_coords))
        w, h = int(max(x_coords) - x), int(max(y_coords) - y)
        
        boxes.append({
            "text": text,
            "conf": conf * 100,
            "bbox": [x, y, w, h]
        })
    
    # Combine text
    result["text"] = "\n".join(texts).strip()
    result["avg_conf"] = sum(confs) / len(confs) if confs else None
    
    if cfg.return_boxes:
        result["boxes"] = boxes
    
    # Extract passport data if requested
    if cfg.doc_type == "passport" and result["text"]:
        passport_data = _extract_passport_data(result["text"])
        result["passport_data"] = passport_data.to_dict()
    
    return result


def pdf_to_images(pdf_bytes: bytes, zoom: float = 2.0) -> List[Image.Image]:
    """
    Render PDF pages to PIL Images. 'zoom' ~ DPI scaling (1.0 ~ 72 DPI).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    imgs: List[Image.Image] = []
    try:
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            imgs.append(img)
    finally:
        doc.close()
    return imgs


def extract_text_pdf(pdf_bytes: bytes, cfg: Optional[OCRConfig] = None, zoom: float = 2.0) -> dict:
    """
    OCR all pages and return combined + per-page results.
    """
    cfg = cfg or OCRConfig()
    pages = pdf_to_images(pdf_bytes, zoom=zoom)
    if not pages:
        return {"text": "", "avg_conf": None, "pages": []}

    all_texts: List[str] = []
    all_confs: List[float] = []
    page_results: List[dict] = []

    for i, pil in enumerate(pages, start=1):
        # Convert PIL to bytes for extract_text
        img_bytes = io.BytesIO()
        pil.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Extract text from page
        page_result = extract_text(img_bytes.getvalue(), cfg)
        page_result["page"] = i
        
        page_results.append(page_result)
        
        if page_result["text"]:
            all_texts.append(page_result["text"])
            if page_result["avg_conf"]:
                all_confs.append(page_result["avg_conf"])

    combined_text = "\n\n".join(all_texts).strip()
    overall_conf = (sum(all_confs) / len(all_confs)) if all_confs else None
    
    result = {"text": combined_text, "avg_conf": overall_conf, "pages": page_results}
    
    # Add combined passport data
    if cfg.doc_type == "passport" and combined_text:
        passport_data = _extract_passport_data(combined_text)
        result["passport_data"] = passport_data.to_dict()

    return result