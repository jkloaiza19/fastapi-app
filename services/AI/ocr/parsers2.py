import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

MONTHS = {
    "jan": "01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
    "jul":"07","aug":"08","sep":"09","sept":"09","oct":"10","nov":"11","dec":"12"
}

@dataclass
class PassportData:
    """Structured passport data"""
    document_type: Optional[str] = None
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
    doc_type: Optional[str] = None
    issuer: Optional[str] = None
    personal_number: Optional[str] = None
    has_expired: Optional[bool] = None
    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

def normalize_ocr(text: str) -> str:
    # unify whitespace and common OCR quirks
    t = text.replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    # normalize funky quotes/apostrophes
    t = t.replace("’", "'").replace("`", "'")
    return t

def find_mrz_lines(text: str):
    # MRZ lines usually have many '<' and are mainly A-Z0-9<
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    candidates = []
    for ln in lines:
        # remove spaces in-case OCR inserted them
        compact = ln.replace(" ", "")
        if compact.count("<") >= 5 and re.fullmatch(r"[A-Z0-9<]+", compact):
            candidates.append(compact)
    return candidates

def mrz_check_digit(s: str) -> str:
    # ICAO 9303 check digit calculation
    values = {**{str(i): i for i in range(10)},
              **{chr(ord('A')+i): 10+i for i in range(26)},
              '<': 0}
    weights = [7, 3, 1]
    total = 0
    for i, ch in enumerate(s):
        total += values.get(ch, 0) * weights[i % 3]
    return str(total % 10)

def parse_date_yyMMdd(yyMMdd: str) -> Optional[str]:
    # MRZ dates are YYMMDD; century is inferred (common approach)
    if not re.fullmatch(r"\d{6}", yyMMdd):
        return None
    yy = int(yyMMdd[:2])
    mm = int(yyMMdd[2:4])
    dd = int(yyMMdd[4:6])

    # heuristic: passport DOB likely in past; expiry likely near future.
    # We'll just map 00-29 -> 2000-2029, else 1900-1999 (adjust as needed).
    year = 2000 + yy if yy <= 29 else 1900 + yy
    try:
        return datetime(year, mm, dd).date().isoformat()
    except ValueError:
        return None

def parse_mrz_td3(line1: str, line2: str) -> PassportData:
    # TD3 format expects 44 chars each, but OCR may alter length slightly.
    # We'll pad/truncate to 44 to be forgiving.
    def fix_len(s): 
        s = s.replace(" ", "")
        return (s + "<"*44)[:44]

    l1 = fix_len(line1)
    l2 = fix_len(line2)

    info = PassportData()
    info.doc_type = l1[0]  # usually 'P'
    info.issuer = l1[2:5].replace("<", "")

    # Names: after issuer, format SURNAME<<GIVEN<NAMES
    names_raw = l1[5:].strip("<")
    parts = names_raw.split("<<", 1)
    surname = parts[0].replace("<", " ").strip() if parts else None
    given = parts[1].replace("<", " ").strip() if len(parts) > 1 else None
    info.surname = surname or None
    info.given_names = given or None

    passport_number = l2[0:9].replace("<", "")
    passport_number_cd = l2[9]
    nationality = l2[10:13].replace("<", "")
    dob = l2[13:19]
    dob_cd = l2[19]
    sex = l2[20].replace("<", "")
    expiry = l2[21:27]
    expiry_cd = l2[27]

    # Optional: validate check digits if present (not always reliable with OCR)
    if re.fullmatch(r"[A-Z0-9<]{9}", l2[0:9]) and passport_number_cd.isdigit():
        if mrz_check_digit(l2[0:9]) == passport_number_cd:
            info.passport_number = passport_number
        else:
            # still keep it if it's plausible
            info.passport_number = passport_number or None
    else:
        info.passport_number = passport_number or None

    info.nationality = nationality or None
    info.date_of_birth = parse_date_yyMMdd(dob)
    info.sex = sex or None
    info.date_of_expiry = parse_date_yyMMdd(expiry)

    return info

def parse_date_human(s: str) -> Optional[str]:
    # Handles "21 Sep 1993", "12 Jan 2028", etc.
    s = s.strip()
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,4})\s+(\d{4})\b", s)
    if not m:
        return None
    dd, mon, yyyy = m.group(1), m.group(2).lower(), m.group(3)
    mon = MONTHS.get(mon[:4], MONTHS.get(mon[:3]))
    if not mon:
        return None
    try:
        return datetime(int(yyyy), int(mon), int(dd)).date().isoformat()
    except ValueError:
        return None

def extract_by_labels(text: str) -> PassportData:
    t = normalize_ocr(text)
    info = PassportData()

    # Surname (very noisy in OCR; try multiple anchors)
    m = re.search(r"\bSurname\b.*?\n([A-Z][A-Z' ]{2,})", t, re.IGNORECASE | re.DOTALL)
    if m: info.surname = m.group(1).strip().replace("  ", " ")

    m = re.search(r"\bGiven\s+Names?\b.*?\n([A-Z][A-Z' ]{2,})", t, re.IGNORECASE | re.DOTALL)
    if m: info.given_names = m.group(1).strip().replace("  ", " ")

    m = re.search(r"\bNationality\b.*?\n([A-Z' ]{3,})", t, re.IGNORECASE | re.DOTALL)
    if m: info.nationality = re.sub(r"\s+", " ", m.group(1)).strip()

    m = re.search(r"\bDate\s+of\s+birth\b.*?\n(.+)", t, re.IGNORECASE)
    if m:
        info.date_of_birth = parse_date_human(m.group(1))

    m = re.search(r"\bdate\s+of\s+expir", t, re.IGNORECASE)
    if m:
        # grab a couple lines after it
        tail = t[m.start():m.start()+120]
        d = parse_date_human(tail)
        if d: info.date_of_expiry = d

    return info

# Main extraction function 
def _only_mrz_chars(s: str) -> str:
    # Keep MRZ alphabet only; convert common OCR separators to nothing
    s = s.upper().replace(" ", "").replace("_", "<")
    return re.sub(r"[^A-Z0-9<]", "", s)

def _parse_date_yyMMdd(yyMMdd: str) -> str:
    # TD3 uses YYMMDD; infer century (standard heuristic)
    yy = int(yyMMdd[:2]); mm = int(yyMMdd[2:4]); dd = int(yyMMdd[4:6])
    year = 2000 + yy if yy <= 29 else 1900 + yy
    return datetime(year, mm, dd).date().isoformat()

def extract_mrz_lines(ocr_text: str) -> tuple[str, str]:
    t = ocr_text.replace("\r", "\n")
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]

    # Candidate line1: starts with P< (often has names)
    line1 = None
    for ln in lines:
        c = _only_mrz_chars(ln)
        if c.startswith("P<") and len(c) >= 10:
            line1 = c
            break

    # Candidate line2: exactly 44 MRZ chars (TD3 passports)
    line2 = None
    for ln in lines:
        c = _only_mrz_chars(ln)
        if len(c) == 44 and re.fullmatch(r"[A-Z0-9<]{44}", c):
            line2 = c
            break

    if not line1 or not line2:
        raise ValueError("Could not find complete MRZ (need a P< line and a 44-char line).")

    # TD3 lines are 44 chars; pad/truncate line1 to be safe
    line1 = (line1 + "<" * 44)[:44]
    return line1, line2

def parse_td3_mrz(line1: str, line2: str) -> PassportData:
    # Line 1
    document_type = line1[0]
    issuer = line1[2:5].replace("<", "")
    names_raw = line1[5:].strip("<")
    surname_part, given_part = (names_raw.split("<<", 1) + [""])[:2]
    surname = surname_part.replace("<", " ").strip()
    given_names = given_part.replace("<", " ").strip()

    # Line 2
    passport_number = line2[0:9].replace("<", "")
    nationality = line2[10:13].replace("<", "")
    dob = _parse_date_yyMMdd(line2[13:19])
    sex = line2[20].replace("<", "")
    exp = _parse_date_yyMMdd(line2[21:27])
    personal_number = line2[28:42]
    has_expired = exp < datetime.now().date().isoformat()

    return PassportData(
        document_type=document_type,
        issuer=issuer,
        surname=surname,
        given_names=given_names,
        passport_number=passport_number,
        nationality=nationality,
        date_of_birth=dob,
        sex=sex,
        date_of_expiry=exp,
        personal_number=personal_number,
        has_expired=has_expired
    )

def extract_passport_from_ocr(ocr_text: str) -> PassportData:
    print(F"Extracting passport data from OCR text...{ocr_text}")
    l1, l2 = extract_mrz_lines(ocr_text)
    print(F"MRZ Lines found:\nL1: {l1}\nL2: {l2}")
    data = parse_td3_mrz(l1, l2)
    print(F"Parsed Passport Data: {data}")
    return data


