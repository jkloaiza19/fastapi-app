# OCR API Documentation

## Overview
The OCR (Optical Character Recognition) service provides powerful text extraction capabilities for images and PDF documents, with specialized support for passport data extraction.

## Features
- **Multi-format support**: PNG, JPEG, TIFF, WebP, PDF
- **Multi-language support**: 80+ languages via EasyOCR
- **Dual OCR engines**: EasyOCR for general text, specialized MRZ parsing for passports
- **Configurable preprocessing**: Grayscale, denoising, thresholding, resizing
- **Bounding box detection**: Optional word-level coordinate extraction
- **PDF support**: Multi-page PDF processing with configurable resolution
- **Passport-specific**: MRZ (Machine Readable Zone) parsing with structured data extraction

## Endpoints

### 1. General OCR - `/v1/ai/ocr/extract`

Extract text from any image or PDF document.

#### Request
```http
POST /v1/ai/ocr/extract
Content-Type: multipart/form-data
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | File | Required | Image or PDF file |
| `lang` | String | `"eng"` | Language codes (e.g., 'eng', 'spa', 'eng+spa') |
| `psm` | Integer | `6` | Page segmentation mode (0-13) |
| `oem` | Integer | `3` | OCR engine mode (0-3) |
| `grayscale` | Boolean | `true` | Convert to grayscale |
| `denoise` | Boolean | `true` | Apply denoising |
| `threshold` | Boolean | `true` | Apply thresholding |
| `resize_factor` | Float | `1.5` | Image resize factor (0.5-4.0) |
| `return_boxes` | Boolean | `false` | Return bounding boxes for detected text |
| `return_pages` | Boolean | `false` | For PDFs, include per-page results |
| `pdf_zoom` | Float | `2.0` | PDF rendering scale (1.0-4.0) |
| `doc_type` | String | `"general"` | Document type: 'general' or 'passport' |

#### Example Request
```bash
curl -X POST "http://localhost:8000/v1/ai/ocr/extract" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.jpg" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=3" \
  -F "grayscale=true" \
  -F "denoise=true" \
  -F "threshold=true" \
  -F "resize_factor=1.5" \
  -F "return_boxes=false"
```

#### Response
```json
{
  "text": "Extracted text content from the document...",
  "confidence": 0.95,
  "preprocessing": {
    "grayscale": true,
    "denoise": true,
    "threshold": true,
    "resize_factor": 1.5
  }
}
```

With `return_boxes=true`:
```json
{
  "text": "Hello World",
  "boxes": [
    {
      "text": "Hello",
      "confidence": 0.98,
      "bbox": [10, 20, 100, 50]
    },
    {
      "text": "World",
      "confidence": 0.96,
      "bbox": [110, 20, 200, 50]
    }
  ]
}
```

### 2. Passport OCR - `/v1/ai/ocr/extract/passport`

Specialized endpoint for passport data extraction with automatic MRZ parsing.

#### Request
```http
POST /v1/ai/ocr/extract/passport
Content-Type: multipart/form-data
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | File | Required | Passport image or PDF |
| `lang` | String | `"eng"` | Language code (recommended: 'eng' for passports) |
| `return_boxes` | Boolean | `false` | Return bounding boxes |
| `pdf_zoom` | Float | `2.0` | PDF rendering scale (1.0-4.0) |

#### Example Request
```bash
curl -X POST "http://localhost:8000/v1/ai/ocr/extract/passport" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@passport.jpg" \
  -F "lang=eng"
```

#### Response
```json
{
  "text": "Full OCR text from passport...",
  "confidence": 0.92,
  "passport_data": {
    "passport_number": "N1234567",
    "surname": "DOE",
    "given_names": "JOHN MICHAEL",
    "nationality": "USA",
    "date_of_birth": "1990-01-15",
    "sex": "M",
    "date_of_expiry": "2030-01-15",
    "country_code": "USA",
    "mrz_line1": "P<USADOE<<JOHN<MICHAEL<<<<<<<<<<<<<<<<<<",
    "mrz_line2": "N1234567<USA9001151M3001151<<<<<<<<<<<<<<<0"
  }
}
```

## Language Support

### Common Language Codes

| Language | Code |
|----------|------|
| English | `eng` |
| Spanish | `spa` |
| French | `fra` |
| German | `deu` |
| Portuguese | `por` |
| Italian | `ita` |
| Russian | `rus` |
| Japanese | `jpn` |
| Korean | `kor` |
| Chinese (Simplified) | `chi_sim` |
| Chinese (Traditional) | `chi_tra` |
| Arabic | `ara` |
| Hindi | `hin` |

### Multi-language
Combine languages with `+`:
```
lang=eng+spa  # English and Spanish
```

## Page Segmentation Modes (PSM)

| Mode | Description |
|------|-------------|
| 0 | Orientation and script detection only |
| 1 | Automatic page segmentation with OSD |
| 2 | Automatic page segmentation without OSD |
| 3 | Fully automatic page segmentation (default) |
| 4 | Single column of text |
| 5 | Single vertical block of text |
| 6 | Single uniform block of text |
| 7 | Single line of text |
| 8 | Single word |
| 9 | Single word in circle |
| 10 | Single character |
| 11 | Sparse text |
| 12 | Sparse text with OSD |
| 13 | Raw line |

**Recommended for passports**: PSM 6 (uniform block of text)

## OCR Engine Modes (OEM)

| Mode | Description |
|------|-------------|
| 0 | Legacy engine only |
| 1 | Neural nets LSTM engine only |
| 2 | Legacy + LSTM engines |
| 3 | Default, based on what is available (recommended) |

## Preprocessing Options

### Grayscale
Converts image to grayscale, often improving OCR accuracy and speed.
- **Default**: `true`
- **Use when**: Processing black and white documents

### Denoise
Applies noise reduction to clean up the image.
- **Default**: `true`
- **Use when**: Image has noise or artifacts

### Threshold
Applies adaptive thresholding to enhance text contrast.
- **Default**: `true`
- **Use when**: Low contrast between text and background

### Resize Factor
Scales the image before OCR processing.
- **Default**: `1.5`
- **Range**: 0.5 to 4.0
- **Passport default**: 2.5 (automatically set)
- **Use higher values**: For small text or low-resolution images
- **Use lower values**: For very high-resolution images or to improve speed

## PDF Processing

### Multi-page PDFs
```bash
curl -X POST "http://localhost:8000/v1/ai/ocr/extract" \
  -F "file=@document.pdf" \
  -F "return_pages=true" \
  -F "pdf_zoom=2.0"
```

Response includes per-page results:
```json
{
  "text": "Combined text from all pages...",
  "pages": [
    {
      "page_number": 1,
      "text": "Text from page 1..."
    },
    {
      "page_number": 2,
      "text": "Text from page 2..."
    }
  ]
}
```

### PDF Zoom
Controls the rendering resolution of PDF pages:
- **Lower values (1.0-1.5)**: Faster processing, lower quality
- **Higher values (2.0-4.0)**: Better quality, slower processing
- **Recommended**: 2.0 for most documents

## Passport Data Extraction

### MRZ (Machine Readable Zone)
The passport endpoint automatically detects and parses the MRZ, which contains:
- Document type (P for passport)
- Issuing country
- Surname and given names
- Passport number
- Nationality
- Date of birth
- Sex
- Date of expiry
- Check digits for validation

### Data Fields

| Field | Description | Example |
|-------|-------------|---------|
| `passport_number` | Passport number | "N1234567" |
| `surname` | Surname/last name | "DOE" |
| `given_names` | Given/first names | "JOHN MICHAEL" |
| `nationality` | Nationality code (3 letters) | "USA" |
| `date_of_birth` | Date of birth (YYYY-MM-DD) | "1990-01-15" |
| `sex` | Sex (M/F) | "M" |
| `date_of_expiry` | Expiry date (YYYY-MM-DD) | "2030-01-15" |
| `country_code` | Issuing country | "USA" |
| `mrz_line1` | First MRZ line | "P<USADOE<<JOHN..." |
| `mrz_line2` | Second MRZ line | "N1234567<USA..." |

## Error Handling

### 400 - Bad Request
```json
{
  "detail": "Unsupported content type: text/plain. Allowed: image/png, image/jpeg, ..."
}
```

### 422 - Unprocessable Entity
```json
{
  "detail": "Could not extract passport data. Please ensure image quality is good and passport is clearly visible."
}
```

### 500 - Internal Server Error
```json
{
  "detail": "OCR failed: [error message]"
}
```

## Best Practices

### Image Quality
- **Resolution**: Minimum 300 DPI recommended
- **Lighting**: Even lighting, avoid shadows
- **Angle**: Document should be flat and straight
- **Focus**: Clear, not blurry

### For Passports
- Ensure the MRZ (bottom two lines) is clearly visible
- Use `resize_factor=2.5` or higher for better MRZ accuracy
- Keep the passport flat to avoid distortion
- Good lighting is critical for MRZ recognition

### Performance Tips
1. Use lower `resize_factor` for large images
2. Disable unnecessary preprocessing (denoise, threshold) if image quality is high
3. For PDFs, use lower `pdf_zoom` if speed is more important than accuracy
4. Cache frequently processed documents

### Security
- Never log or store sensitive passport data without encryption
- Use HTTPS in production
- Implement proper access controls
- Consider data retention policies

## Python Client Example

```python
import requests

# General OCR
with open('document.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/v1/ai/ocr/extract',
        files={'file': f},
        data={
            'lang': 'eng',
            'psm': 6,
            'return_boxes': True
        }
    )
    
result = response.json()
print(f"Extracted text: {result['text']}")

# Passport OCR
with open('passport.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/v1/ai/ocr/extract/passport',
        files={'file': f}
    )
    
passport = response.json()
print(f"Passport Number: {passport['passport_data']['passport_number']}")
print(f"Name: {passport['passport_data']['given_names']} {passport['passport_data']['surname']}")
```

## JavaScript Client Example

```javascript
// General OCR
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('lang', 'eng');
formData.append('return_boxes', 'true');

const response = await fetch('http://localhost:8000/v1/ai/ocr/extract', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Extracted text:', result.text);

// Passport OCR
const passportFormData = new FormData();
passportFormData.append('file', passportFile);

const passportResponse = await fetch('http://localhost:8000/v1/ai/ocr/extract/passport', {
  method: 'POST',
  body: passportFormData
});

const passport = await passportResponse.json();
console.log('Passport data:', passport.passport_data);
```

## Troubleshooting

### Poor OCR Accuracy
1. Increase `resize_factor` (try 2.0 or higher)
2. Ensure good image quality
3. Try different `psm` values
4. Enable all preprocessing options

### Passport MRZ Not Detected
1. Ensure MRZ lines are clearly visible
2. Increase `resize_factor` to 2.5 or higher
3. Verify image is not skewed or distorted
4. Check lighting and contrast

### Slow Processing
1. Reduce `resize_factor`
2. Disable unnecessary preprocessing
3. For PDFs, lower `pdf_zoom`
4. Consider GPU acceleration (set `gpu=true` in OCRConfig)

### SSL Certificate Errors (macOS)
The application automatically configures SSL certificates using certifi. If you encounter SSL errors:
1. Ensure certifi is installed: `poetry install`
2. The fix is already applied in `services/AI/ocr/ocr2.py`
