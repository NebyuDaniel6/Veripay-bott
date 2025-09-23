import re
from typing import Dict, Any
from .base import extract_first, number_candidates, to_confidence, clean_amount_str


def extract_fields(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"bank": "Bank of Abyssinia"}

    # Amount: keyworded first, else largest plausible ETB amount
    amount = extract_first([
        r"(?:amount|total|paid)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:ETB|Br)?",
        r"(?:ETB|Br)\s*([\d,]+(?:\.\d+)?)",
    ], text)
    if not amount:
        cands = number_candidates(text)
        if cands:
            amount = f"{max(cands):.2f}"
    if amount:
        try:
            data["amount"] = float(clean_amount_str(amount))
            data["amount_confidence"] = to_confidence(True)
        except Exception:
            pass

    # Sender/Beneficiary
    sender = extract_first([
        r"(?:from|sender|payer|remitter|debited\s+from)\s*[:\-]?\s*([A-Za-z][\w\s\.-]{2,})",
        r"beneficiary\s*[:\-]?\s*([A-Za-z][\w\s\.-]{2,})",
        r"account\s*name\s*[:\-]?\s*([A-Za-z][\w\s\.-]{2,})",
    ], text)
    if sender:
        data["sender"] = sender
        data["sender_confidence"] = to_confidence(True, 0.8)

    # Reference: common variants
    ref = extract_first([
        r"(?:ref(?:erence)?\s*(?:no\.?|#)?|ft\s*ref|trx\s*id|transaction\s*id)\s*[:\-]?\s*([A-Z0-9\-]{5,})",
    ], text, flags=re.IGNORECASE)
    if ref:
        data["reference"] = ref
        data["reference_confidence"] = to_confidence(True, 0.9)

    # Date/Time
    date = extract_first([
        r"(?:date\/?time|date|time|transaction\s*time)\s*[:\-]?\s*([\d]{4}[\-/][\d]{1,2}[\-/][\d]{1,2}[ T][\d]{1,2}:[\d]{2}(?::[\d]{2})?(?:\s*[AP]M)?)",
        r"([\d]{1,2}[\-/][\d]{1,2}[\-/][\d]{2,4}\s+[\d]{1,2}:[\d]{2}(?::[\d]{2})?(?:\s*[AP]M)?)",
    ], text)
    if date:
        data["time"] = date
        data["time_confidence"] = to_confidence(True, 0.7)

    return data 