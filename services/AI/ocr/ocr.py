from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import io

import numpy as np
from PIL import Image
import cv2
import pytesseract
import fitz
import re 


@dataclass
class OCRConfig:
    lang: str = "eng"
    psm: int = 6
    oem: int = 3
    grayscale: bool = True
    denoise: bool = True
    threshold: bool = True
    resize_factor: float = 1.5
    return_boxes: bool = False
    doc_type: Optional[str] = None

@dataclass
class PassportData:
    """Structured passport data"""
    passport_number: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = None
    place_of_birth: Optional[str] = None
    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None
    issuing_authority: Optional[str] = None
    country_code: Optional[str] = None
    mrz_line1: Optional[str] = None
    mrz_line2: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _load_image(bytes_data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(bytes_data)).convert("RGB")


def _preprocess(img: Image.Image, cfg: OCRConfig) -> np.ndarray:
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    if cfg.grayscale:
        cv = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)

    if cfg.resize_factor and cfg.resize_factor > 1.0:
        h, w = cv.shape[:2]
        cv = cv2.resize(cv, (int(w * cfg.resize_factor), int(h * cfg.resize_factor)), interpolation=cv2.INTER_CUBIC)

    if cfg.denoise:
        cv = cv2.fastNlMeansDenoising(cv, None, h=7, templateWindowSize=7) if len(cv.shape) == 2 else cv

    if cfg.threshold:
        if len(cv.shape) == 2:
            _, cv = cv2.threshold(cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return cv


def _tesseract_config(cfg: OCRConfig) -> str:
    return f"-l {cfg.lang} --psm {cfg.psm} --oem {cfg.oem}"


def _clean_text(text: str) -> str:
    """Clean OCR artifacts from text"""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove common OCR noise characters
    text = re.sub(r'[|+~_]', '', text)
    return text.strip()


def _extract_passport_data(text: str) -> PassportData:
    """Extract structured data from passport OCR text"""
    data = PassportData()
    
    # Clean the text
    text = _clean_text(text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Try to find MRZ lines (Machine Readable Zone)
    # MRZ lines are typically 44 characters long and contain only A-Z, 0-9, and <
    mrz_pattern = r'^[A-Z0-9<]{40,44}$'
    mrz_lines = []
    
    for line in lines:
        cleaned_line = line.replace(' ', '').replace('|', 'I').replace('1', 'I').replace('0', 'O')
        if re.match(mrz_pattern, cleaned_line) and len(cleaned_line) >= 40:
            mrz_lines.append(cleaned_line)
    
    # Process MRZ if found
    if len(mrz_lines) >= 2:
        data.mrz_line1 = mrz_lines[-2][:44]
        data.mrz_line2 = mrz_lines[-1][:44]
        
        # Parse MRZ Line 1: P<COUNTRY_CODE<SURNAME<<GIVEN_NAMES
        mrz1 = data.mrz_line1
        if mrz1.startswith('P<'):
            data.country_code = mrz1[2:5].replace('<', '').strip()
            names_section = mrz1[5:44]
            parts = names_section.split('<<')
            if len(parts) >= 1:
                data.surname = parts[0].replace('<', ' ').strip()
            if len(parts) >= 2:
                data.given_names = parts[1].replace('<', ' ').strip()
        
        # Parse MRZ Line 2
        mrz2 = data.mrz_line2
        if len(mrz2) >= 44:
            # Passport number (chars 0-8)
            data.passport_number = mrz2[:9].replace('<', '').strip()
            
            # Nationality (chars 10-12)
            data.nationality = mrz2[10:13].replace('<', '').strip()
            
            # Date of birth (chars 13-18, format YYMMDD)
            dob = mrz2[13:19]
            if dob[:6].isdigit():
                yy, mm, dd = dob[:2], dob[2:4], dob[4:6]
                year = f"19{yy}" if int(yy) > 50 else f"20{yy}"
                data.date_of_birth = f"{year}-{mm}-{dd}"
            
            # Sex (char 20)
            if mrz2[20] in ['M', 'F', 'X']:
                data.sex = mrz2[20]
            
            # Date of expiry (chars 21-26, format YYMMDD)
            expiry = mrz2[21:27]
            if expiry[:6].isdigit():
                yy, mm, dd = expiry[:2], expiry[2:4], expiry[4:6]
                data.date_of_expiry = f"20{yy}-{mm}-{dd}"
    
    # Fallback: Extract from text patterns
    text_upper = text.upper()
    
    # Extract country/nationality
    if not data.country_code:
        country_patterns = [
            r'(?:UNITED\s+STATES|USA|U\.S\.A\.)',
            r'(?:CANADA|CAN)',
            r'(?:MEXICO|MEX)',
        ]
        for pattern in country_patterns:
            if re.search(pattern, text_upper):
                if 'UNITED STATES' in text_upper or 'USA' in text_upper:
                    data.country_code = 'USA'
                    data.nationality = 'USA'
                break
    
    # Extract passport number
    if not data.passport_number:
        # Look for patterns like "PASSPORT CARD" followed by number, or standalone alphanumeric
        passport_patterns = [
            r'(?:PASSPORT\s+(?:CARD|NO|NUMBER)?[\s:]*)?([A-Z0-9]{6,12})',
            r'No[\s.:]+([A-Z0-9]{6,12})',
        ]
        for pattern in passport_patterns:
            match = re.search(pattern, text_upper)
            if match:
                candidate = match.group(1)
                # Filter out common false positives
                if not re.match(r'^(PASSPORT|CARD|USA|STATES|AMERICA)$', candidate):
                    data.passport_number = candidate
                    break
    
    # Extract surname
    if not data.surname:
        surname_patterns = [
            r'(?:Surname|Last\s+Name|Sur)[\s:]+([A-Z][A-Z\s]+?)(?:\s+Given|\s+\d|\s*$)',
            r'^([A-Z]{2,})\s+[A-Z][a-z]+',  # All caps followed by title case
        ]
        for pattern in surname_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                surname = match.group(1).strip()
                if len(surname) > 1 and not re.match(r'^(PASSPORT|UNITED|STATES)$', surname.upper()):
                    data.surname = surname
                    break
    
    # Extract given names
    if not data.given_names:
        given_patterns = [
            r'(?:Given\s+Names?|First\s+Name)[\s:]+([A-Z][A-Za-z\s]+?)(?:\s+Sex|\s+Date|\s+Place|\s*$)',
            r'Names?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        for pattern in given_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                names = match.group(1).strip()
                if len(names) > 1:
                    data.given_names = names
                    break
    
    # Extract date of birth
    if not data.date_of_birth:
        dob_patterns = [
            r'(?:Date\s+of\s+Birth|Birth|DOB)[\s:]+(\d{1,2}\s+[A-Z]{3}\s+\d{4})',
            r'(?:Date\s+of\s+Birth|Birth|DOB)[\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dob_str = match.group(1)
                # Try to parse common formats
                if re.match(r'\d{1,2}\s+[A-Z]{3}\s+\d{4}', dob_str.upper()):
                    data.date_of_birth = dob_str
                break
    
    # Extract sex/gender
    if not data.sex:
        sex_patterns = [
            r'(?:Sex|Gender)[\s:]+([MFX])',
            r'\b([MF])\b(?=\s+\d{1,2}\s+[A-Z]{3})',  # M or F before date
        ]
        for pattern in sex_patterns:
            match = re.search(pattern, text_upper)
            if match:
                data.sex = match.group(1)
                break
    
    # Extract place of birth
    if not data.place_of_birth:
        pob_match = re.search(r'(?:Place\s+of\s+Birth)[\s:]+([A-Z][A-Za-z\s,\.]+?)(?:\s+Date|\s+Sex|\s*$)', text, re.IGNORECASE)
        if pob_match:
            data.place_of_birth = pob_match.group(1).strip()
    
    # Extract issuing authority/department
    if not data.issuing_authority:
        auth_match = re.search(r'(DEPARTMENT\s+OF\s+STATE|ISSUING\s+AUTHORITY)[^\n]*', text_upper)
        if auth_match:
            data.issuing_authority = auth_match.group(0).strip()
    
    return data


def extract_text(image_bytes: bytes, cfg: Optional[OCRConfig] = None) -> dict:
    """
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
    tess_cfg = _tesseract_config(cfg)

    result = {
        "text": "",
        "avg_conf": None,
        "boxes": [],
    }

    if cfg.return_boxes:
        data = pytesseract.image_to_data(proc, config=tess_cfg, output_type=pytesseract.Output.DICT)
        texts: List[str] = []
        confs: List[float] = []
        boxes: List[Tuple[int, int, int, int]] = []

        for i in range(len(data["text"])):
            txt = data["text"][i].strip()
            conf = float(data["conf"][i]) if str(data["conf"][i]).isdigit() else -1.0
            if txt:
                texts.append(txt)
                confs.append(conf)
                boxes.append((data["left"][i], data["top"][i], data["width"][i], data["height"][i]))

        result["text"] = " ".join(texts).strip()
        if confs:
            valid = [c for c in confs if c >= 0]
            result["avg_conf"] = (sum(valid) / len(valid)) if valid else None
        result["boxes"] = [
            {"text": t, "conf": c if c >= 0 else None, "bbox": [x, y, w, h]}
            for t, c, (x, y, w, h) in zip(texts, confs, boxes)
        ]
    else:
        text = pytesseract.image_to_string(proc, config=tess_cfg)
        result["text"] = text.strip()
    
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
        proc = _preprocess(pil, cfg)
        tess_cfg = _tesseract_config(cfg)

        if cfg.return_boxes:
            data = pytesseract.image_to_data(proc, config=tess_cfg, output_type=pytesseract.Output.DICT)
            texts, confs, boxes = [], [], []
            for j in range(len(data["text"])):
                txt = data["text"][j].strip()
                conf_raw = data["conf"][j]
                conf = float(conf_raw) if str(conf_raw).replace('.', '', 1).isdigit() else -1.0
                if txt:
                    texts.append(txt)
                    confs.append(conf)
                    boxes.append((data["left"][j], data["top"][j], data["width"][j], data["height"][j]))
            page_text = " ".join(texts).strip()
            valid = [c for c in confs if c >= 0]
            avg_conf = (sum(valid) / len(valid)) if valid else None

            page_result = {
                "page": i,
                "text": page_text,
                "avg_conf": avg_conf,
                "boxes": [
                    {"text": t, "conf": (c if c >= 0 else None), "bbox": [x, y, w, h]}
                    for t, c, (x, y, w, h) in zip(texts, confs, boxes)
                ],
            }
            
            if cfg.doc_type == "passport" and page_text:
                passport_data = _extract_passport_data(page_text)
                page_result["passport_data"] = passport_data.to_dict()
            
            page_results.append(page_result)
            if page_text:
                all_texts.append(page_text)
                all_confs.extend(valid)
        else:
            page_text = pytesseract.image_to_string(proc, config=tess_cfg).strip()
            page_result = {"page": i, "text": page_text, "avg_conf": None, "boxes": []}
            
            if cfg.doc_type == "passport" and page_text:
                passport_data = _extract_passport_data(page_text)
                page_result["passport_data"] = passport_data.to_dict()
            
            page_results.append(page_result)
            if page_text:
                all_texts.append(page_text)

    combined_text = "\n\n".join(all_texts).strip()
    overall_conf = (sum(all_confs) / len(all_confs)) if all_confs else None
    
    result = {"text": combined_text, "avg_conf": overall_conf, "pages": page_results}
    
    # Add combined passport data
    if cfg.doc_type == "passport" and combined_text:
        passport_data = _extract_passport_data(combined_text)
        result["passport_data"] = passport_data.to_dict()

    return result