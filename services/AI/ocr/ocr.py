from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import io

import numpy as np
from PIL import Image
import cv2
import pytesseract
import fitz


@dataclass
class OCRConfig:
    lang: str = "eng"         # installed language codes, e.g., "eng", "spa", "eng+spa"
    psm: int = 6              # Page Segmentation Mode (0-13). 6: Assume a uniform block of text.
    oem: int = 3              # OCR Engine Mode (0-3). 3: Default, based on what is available.
    grayscale: bool = True
    denoise: bool = True
    threshold: bool = True
    resize_factor: float = 1.5
    return_boxes: bool = False


def _load_image(bytes_data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(bytes_data)).convert("RGB")


def _preprocess(img: Image.Image, cfg: OCRConfig) -> np.ndarray:
    # Convert to OpenCV (BGR)
    cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    if cfg.grayscale:
        cv = cv2.cvtColor(cv, cv2.COLOR_BGR2GRAY)

    if cfg.resize_factor and cfg.resize_factor > 1.0:
        h, w = cv.shape[:2]
        cv = cv2.resize(cv, (int(w * cfg.resize_factor), int(h * cfg.resize_factor)), interpolation=cv2.INTER_CUBIC)

    if cfg.denoise:
        # Mild denoise to help OCR (works for grayscale or color)
        cv = cv2.fastNlMeansDenoising(cv, None, h=7, templateWindowSize=7) if len(cv.shape) == 2 else cv

    if cfg.threshold:
        # Otsu threshold for binarization (works only on grayscale)
        if len(cv.shape) == 2:
            _, cv = cv2.threshold(cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return cv


def _tesseract_config(cfg: OCRConfig) -> str:
    return f"-l {cfg.lang} --psm {cfg.psm} --oem {cfg.oem}"


def extract_text(image_bytes: bytes, cfg: Optional[OCRConfig] = None) -> dict:
    """
    Returns:
      {
        "text": "...",
        "avg_conf": float | None,
        "boxes": [ { "text": str, "conf": float, "bbox": [x, y, w, h] }, ... ] (if cfg.return_boxes)
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
        return result

    text = pytesseract.image_to_string(proc, config=tess_cfg)
    result["text"] = text.strip()
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

            page_results.append({
                "page": i,
                "text": page_text,
                "avg_conf": avg_conf,
                "boxes": [
                    {"text": t, "conf": (c if c >= 0 else None), "bbox": [x, y, w, h]}
                    for t, c, (x, y, w, h) in zip(texts, confs, boxes)
                ],
            })
            if page_text:
                all_texts.append(page_text)
                all_confs.extend(valid)
        else:
            page_text = pytesseract.image_to_string(proc, config=tess_cfg).strip()
            page_results.append({"page": i, "text": page_text, "avg_conf": None, "boxes": []})
            if page_text:
                all_texts.append(page_text)

    combined_text = "\n\n".join(all_texts).strip()
    overall_conf = (sum(all_confs) / len(all_confs)) if all_confs else None

    return {"text": combined_text, "avg_conf": overall_conf, "pages": page_results}