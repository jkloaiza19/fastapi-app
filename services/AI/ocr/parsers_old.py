from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{30,}$")


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", s.upper())


def _fix_digits_for_codes(s: str) -> str:
    # Fix common OCR digit→letter confusions in country codes / nationality
    return s.replace("5", "S").replace("0", "O").replace("1", "I").replace("2", "Z").replace("8", "B")


def _find_mrz_lines_raw(text: str) -> Tuple[Optional[str], Optional[str]]:
    # Keep raw lines for parsing names; use normalized copies only for detection
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    norm = [_norm(l) for l in lines]
    # line1: last starting with P<
    l1_idx = next((len(norm) - 1 - i for i, x in enumerate(reversed(norm)) if x.startswith("P<")), None)
    # line2: last MRZ-like with a 6-digit run
    l2_idx = None
    for i, x in enumerate(reversed(norm)):
        if MRZ_LINE_RE.match(x) and re.search(r"\d{6}", x):
            l2_idx = len(norm) - 1 - i
            break
    raw_l1 = lines[l1_idx] if l1_idx is not None else None
    raw_l2 = lines[l2_idx] if l2_idx is not None else None
    return raw_l1, raw_l2


def _parse_yyMMdd(yyMMdd: str) -> Optional[str]:
    if not re.match(r"^\d{6}$", yyMMdd):
        return None
    yy = int(yyMMdd[0:2]); mm = int(yyMMdd[2:4]); dd = int(yyMMdd[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None
    cur_two = int(datetime.utcnow().strftime("%y"))
    century = 1900 if yy > cur_two else 2000
    try:
        return datetime(century + yy, mm, dd).strftime("%Y-%m-%d")
    except Exception:
        return None


def _normalize_date_ocr(s: str) -> str:
    return s.replace("I", "1").replace("l", "1").replace("O", "0").replace("S", "5").strip()


def _parse_date_flexible(s: str) -> Optional[str]:
    s = _normalize_date_ocr(s)
    fmts = ["%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%m/%d/%Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).strftime("%Y-%m-%d")
        except Exception:
            pass
    m = re.match(r"^(\d{2})(\d{2})(\d{4})$", s)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mth, d).strftime("%Y-%m-%d")
        except Exception:
            return None
    return None


def parse_mrz(text: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {
        "passport_number": None,
        "surname": None,
        "given_names": None,
        "nationality": None,
        "sex": None,
        "date_of_birth": None,
        "expiration_date": None,
        "issuing_country": None,
    }
    raw_l1, raw_l2 = _find_mrz_lines_raw(text)
    if not raw_l1 and not raw_l2:
        return out

    # Line 1: parse names and issuing country from RAW (no digit swaps)
    if raw_l1 and raw_l1.strip().upper().startswith("P<"):
        norm_l1 = _norm(raw_l1)[:44].ljust(44, "<")
        out["issuing_country"] = _fix_digits_for_codes(norm_l1[2:5]).replace("<", "") or None
        # After P<CCC, names with << separator and < as spaces
        name_section = raw_l1.strip()[5:]
        parts = name_section.split("<<", 1)
        surname = parts[0].replace("<", " ").strip()
        given = parts[1].replace("<", " ").strip() if len(parts) > 1 else None
        out["surname"] = surname or None
        out["given_names"] = given or None

    # Line 2: parse numbers/dates from normalized copy
    if raw_l2:
        l2 = _norm(raw_l2)[:44].ljust(44, "<")
        pn = l2[0:9].replace("<", "").strip() or None
        out["passport_number"] = pn
        out["nationality"] = _fix_digits_for_codes(l2[10:13]).replace("<", "") or None
        out["date_of_birth"] = _parse_yyMMdd(l2[13:19])
        out["sex"] = {"M": "M", "F": "F"}.get(l2[20], "X")
        out["expiration_date"] = _parse_yyMMdd(l2[21:27])

    return out


def heuristic_passport(text: str) -> Dict[str, Optional[str]]:
    def pick_inline(patterns: List[str]) -> Optional[str]:
        for p in patterns:
            m = re.search(p, text, flags=re.I)
            if m:
                return m.group(1).strip()
        return None

    def pick_next_line(labels: List[str]) -> Optional[str]:
        lines = [l.strip() for l in text.splitlines()]
        for i, l in enumerate(lines):
            for lp in labels:
                if re.search(lp, l, flags=re.I):
                    if i + 1 < len(lines):
                        nxt = re.sub(r"^[\-\:\s'’]+", "", lines[i + 1]).strip()
                        return nxt
        return None

    # Passport number: require digits to avoid capturing "PASAPORTE"
    passport_number = pick_inline([
        r"Passport\s*(?:No\.?|Number)[:\s]*([A-Z0-9][A-Z0-9\s]{5,12})",
        r"Document\s*(?:No\.?|Number)[:\s]*([A-Z0-9][A-Z0-9\s]{5,12})",
    ])
    if not passport_number:
        pn_next = pick_next_line([r"Passport\s*(?:No\.?|Number)", r"Document\s*(?:No\.?|Number)"])
        if pn_next and re.search(r"\d", pn_next):
            passport_number = pn_next
    if passport_number:
        passport_number = re.sub(r"\s+", "", passport_number)

    nationality = pick_inline([r"\bNationality\b[:\s]*([A-Z][A-Za-z\s]{2,})"]) or pick_next_line([r"\bNationality\b"])
    if nationality:
        nationality = re.sub(r"^[Aa]\s+", "", nationality).strip()

    place_of_birth = pick_inline([r"(?:Place\s*of\s*Birth)[:\s]*([A-Za-z\s\-\(\)]{3,})"]) or pick_next_line([r"Place\s*of\s*Birth"])

    date_pat = r"([0-9]{1,2}[\-\/\. ][0-9]{1,2}[\-\/\. ][0-9]{2,4}|[0-9]{1,2}\s+[A-Za-z]{3,}\s+[0-9]{4})"
    dob_raw = pick_inline([rf"(?:Date\s*of\s*Birth|DOB)[:\s'\-]*{date_pat}"]) or pick_next_line([r"Date\s*of\s*Birth", r"\bDOB\b"])
    exp_raw = pick_inline([rf"(?:Date\s*of\s*Expiry|Expiry|Expires)[:\s'\-]*{date_pat}"]) or pick_next_line([r"(?:Date\s*of\s*Expiry|Expiry|Expires)"])
    iss_raw = pick_inline([rf"(?:Date\s*of\s*Issue|Issued\s*On)[:\s'\-]*{date_pat}"]) or pick_next_line([r"(?:Date\s*of\s*Issue|Issued\s*On)"])

    surname = pick_inline([r"(?:Surname|Last\s*Name)[:\s]*([A-Z][A-Za-z\-\s]{1,})"]) or pick_next_line([r"(?:Surname|Last\s*Name)"])
    given_names = pick_inline([r"(?:Given\s*Names?|First\s*Name)[:\s]*([A-Z][A-Za-z\-\s]{1,})"]) or pick_next_line([r"(?:Given\s*Names?|First\s*Name)"])
    sex = pick_inline([r"(?:Sex|Gender)[:\s]*([MF])"]) or pick_next_line([r"(?:Sex|Gender)"])

    return {
        "passport_number": passport_number if (passport_number and re.search(r"\d", passport_number)) else None,
        "surname": surname,
        "given_names": given_names,
        "nationality": nationality,
        "sex": (sex if sex in ("M", "F") else None),
        "date_of_birth": _parse_date_flexible(dob_raw) if dob_raw else None,
        "expiration_date": _parse_date_flexible(exp_raw) if exp_raw else None,
        "issue_date": _parse_date_flexible(iss_raw) if iss_raw else None,
        "issuing_country": None,
        "place_of_birth": place_of_birth,
    }


def extract_passport_fields(text: str, mrz_text: Optional[str] = None) -> Dict[str, Optional[str]]:
    mrz = parse_mrz(mrz_text or "") if mrz_text else {}
    heur = heuristic_passport(text)
    return {
        "passport_number": mrz.get("passport_number") or heur.get("passport_number"),
        "surname": mrz.get("surname") or heur.get("surname"),
        "given_names": mrz.get("given_names") or heur.get("given_names"),
        "nationality": mrz.get("nationality") or heur.get("nationality"),
        "sex": mrz.get("sex") or heur.get("sex"),
        "date_of_birth": mrz.get("date_of_birth") or heur.get("date_of_birth"),
        "expiration_date": mrz.get("expiration_date") or heur.get("expiration_date"),
        "issue_date": heur.get("issue_date"),
        "issuing_country": mrz.get("issuing_country") or heur.get("issuing_country"),
        "place_of_birth": heur.get("place_of_birth"),
    }