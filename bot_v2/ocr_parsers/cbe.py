import re
from typing import Dict, Any, Optional
from .base import extract_first, number_candidates, to_confidence, clean_amount_str


FEE_KEYWORDS = re.compile(r"\b(fee|charge|service\s*charge|vat|commission)\b", re.IGNORECASE)
AMOUNT_LABELS = [
    r"(?:amount|total|paid)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:ETB|Br)?",
    r"(?:ETB|Br)\s*([\d,]+(?:\.\d+)?)",
]

# Common CBE confirmations that precede the main amount
SUCCESS_ANCHORS = [
    "You have successfully transferred",
    "Transfer successful",
    "Transaction successful",
    "Payment successful",
]

# CBE reference patterns
REF_PATTERNS = [
    r"(?:Ref(?:erence)?\s*(?:No\.?|#)?|Trans(?:action)?\s*(?:ID|No\.?))\s*[:\-]?\s*([A-Z0-9\-]{6,})",
    r"\bFT\s*Ref\s*[:\-]?\s*([A-Z0-9\-]{6,})",
]

DATE_PATTERNS = [
    r"Date\s*[:\-]?\s*([0-3]?\d[\-/][0-1]?\d[\-/](?:\d{2}|\d{4})\s+[0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?(?:\s*(?:AM|PM))?)",
    r"Date\s*&\s*Time\s*[:\-]?\s*([0-3]?\d[\-/][0-1]?\d[\-/](?:\d{2}|\d{4})\s+[0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?(?:\s*(?:AM|PM))?)",
    r"([0-3]?\d\s+[A-Za-z]{3,9}\s+\d{4}\s+[0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?(?:\s*(?:AM|PM))?)",
    r"(\d{4}[\-/][0-1]?\d[\-/][0-3]?\d\s+[0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?)",
]

SENDER_PATTERNS = [
    r"(?:From|Sender|Account\s*Name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s'.-]{1,60})",
]


def _largest_non_fee_amount(text: str) -> Optional[float]:
    best: Optional[float] = None
    # Prefer labeled amounts first
    for pat in AMOUNT_LABELS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if FEE_KEYWORDS.search(line):
                continue
            try:
                val = float(clean_amount_str(m.group(1)))
                if best is None or val > best:
                    best = val
            except Exception:
                continue
    # If none found, consider all numeric candidates excluding fee lines
    if best is None:
        for m in re.finditer(r"(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+|\d+)(?:\s*(?:ETB|Br))?", text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end]
            if FEE_KEYWORDS.search(line):
                continue
            try:
                val = float(clean_amount_str(m.group(1)))
                if best is None or val > best:
                    best = val
            except Exception:
                continue
    return best


def extract_fields(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"bank": "Commercial Bank of Ethiopia"}

    # Try to scope around success anchors to find the primary amount
    lower = text.lower()
    amount: Optional[float] = None
    for a in SUCCESS_ANCHORS:
        idx = lower.find(a.lower())
        if idx != -1:
            window = text[idx: idx + 800]
            amount = _largest_non_fee_amount(window)
            if amount:
                break
    # Fallback to global scan
    if amount is None:
        amount = _largest_non_fee_amount(text)
    if amount is not None:
        data["amount"] = amount
        data["amount_confidence"] = to_confidence(True)

    # Reference
    ref = extract_first(REF_PATTERNS, text)
    if ref:
        data["reference"] = ref
        data["reference_confidence"] = to_confidence(True)

    # Date/Time
    dt = extract_first(DATE_PATTERNS, text)
    if dt:
        data["time"] = dt
        data["time_confidence"] = to_confidence(True)

    # Sender
    sender = extract_first(SENDER_PATTERNS, text)
    if sender:
        data["sender"] = sender
        data["sender_confidence"] = to_confidence(True)

    return data 