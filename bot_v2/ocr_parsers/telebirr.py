import re
from typing import Dict, Any, Optional
from .base import extract_first, number_candidates, to_confidence, clean_amount_str


def _extract_sender_clean(text: str) -> Optional[str]:
    """Extract sender name with noise removal for Telebirr"""
    
    # Look for sender patterns - don't cross newlines
    sender_patterns = [
        r"(?:From|Sender|Payer|Customer\s*Name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s'.-]{1,60}?)(?:\n|$)",
        r"Customer\s*Name\s*[:\-]?\s*([A-Za-z][A-Za-z\s'.-]{1,60}?)(?:\n|$)",
    ]
    
    for pattern in sender_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            potential_sender = match.group(1).strip()
            
            # Remove common Telebirr noise - be more aggressive
            cleaned = re.sub(r"\s+(abroad\s+via\s+telebirr.*)$", "", potential_sender, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+(Get|Download.*)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+(via\s+telebirr.*)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+(Date.*)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+(Transaction.*)$", "", cleaned, flags=re.IGNORECASE).strip()
            
            # Remove trailing numbers/amounts
            cleaned = re.sub(r"\s+\d+[.,]\d+\s*(ETB|Br)?$", "", cleaned, flags=re.IGNORECASE).strip()
            
            # If the cleaned result is just noise, return None instead of trying to find a name
            if cleaned.lower() in ["abroad", "via", "telebirr", "get", "download", "payment", "successful"]:
                continue
            
            # Must start with letter and contain letters
            if re.match(r"^[A-Za-z]", cleaned) and re.search(r"[A-Za-z]", cleaned):
                return cleaned
    
    return None


def extract_fields(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"bank": "Telebirr"}

    # Amount: Look for labeled amounts first, then largest number
    amount = extract_first([
        r"(?:amount|paid|total)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(?:ETB|Br)?",
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

    # Sender: Use robust extraction
    sender = _extract_sender_clean(text)
    if sender:
        data["sender"] = sender
        data["sender_confidence"] = to_confidence(True)

    # Date/Time: Multiple patterns
    dt = extract_first([
        r"Date\s*[:\-]?\s*([0-3]?\d[\-/][0-1]?\d[\-/](?:\d{2}|\d{4})\s+[0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?(?:\s*(?:AM|PM))?)",
        r"Time\s*[:\-]?\s*([0-2]?\d[:][0-5]\d(?:[:][0-5]\d)?(?:\s*(?:AM|PM))?)",
        r"([0-3]?\d[\-/][0-1]?\d[\-/](?:\d{2}|\d{4}))", # Just date
        r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}\s+[0-2]?\d[:][0-5]\d)",
    ], text)
    if dt:
        data["time"] = dt
        data["time_confidence"] = to_confidence(True)

    # Reference: Look for transaction numbers
    ref = extract_first([
        r"(?:Transaction\s*No|Trans\s*No|Txn\s*No|Transaction\s*ID|Trans\s*ID|Txn\s*ID)\s*[:\-]?\s*([A-Z0-9]{5,})",
        r"Ref(?:erence)?\s*(?:No\.?|#)?\s*[:\-]?\s*([A-Z0-9]{5,})",
        r"ID\s*[:\-]?\s*([A-Z0-9]{5,})",
    ], text)
    if ref:
        data["reference"] = ref
        data["reference_confidence"] = to_confidence(True)

    return data
