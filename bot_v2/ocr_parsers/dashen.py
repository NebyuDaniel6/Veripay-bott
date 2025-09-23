import re
from typing import Dict, Any, Optional
from .base import extract_first, number_candidates, to_confidence, clean_amount_str


SUCCESS_ANCHORS = [
    "Money Successfully Sent",
    "You have successfully sent money",
]

FEE_KEYWORDS = re.compile(r"\b(fee|charge|service\s*charge|vat|commission)\b", re.IGNORECASE)

def _largest_non_fee_amount_near_anchor(text: str, anchor_idx: int) -> Optional[float]:
    best_amount: Optional[float] = None
    window = text[anchor_idx: anchor_idx + 600]
    lines = window.split('\n')
    for line in lines:
        if FEE_KEYWORDS.search(line):
            continue
        cands = number_candidates(line)
        if cands:
            current_max_line_amount = max(cands)
            if best_amount is None or current_max_line_amount > best_amount:
                best_amount = current_max_line_amount
    if best_amount is None:
        cands_in_window = number_candidates(window)
        if cands_in_window:
            best_amount = max(cands_in_window)
    return best_amount


def _extract_sender_name_robust(text: str) -> Optional[str]:
    """Extract sender name with very strict validation to avoid capturing amounts"""
    
    # Look for "Sender Name:" pattern specifically - don't cross newlines
    sender_patterns = [
        r"sender\s*name\s*[:\-]?\s*([A-Za-z][A-Za-z\s'.-]{1,60}?)(?:\n|$)",
        r"from\s*[:\-]?\s*([A-Za-z][A-Za-z\s'.-]{1,60}?)(?:\n|$)",
    ]
    
    for pattern in sender_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            potential_sender = match.group(1).strip()
            
            # Strict validation: must start with letter, contain letters, and not be mostly numbers
            if not re.match(r"^[A-Za-z]", potential_sender):
                continue
                
            # Must contain at least 2 letters
            if len(re.findall(r"[A-Za-z]", potential_sender)) < 2:
                continue
                
            # Cannot be mostly numbers or contain amount patterns
            if re.search(r"\d+[.,]\d+", potential_sender):
                continue
                
            # Cannot contain ETB, Br, or currency symbols (fixed regex)
            if re.search(r"\b(ETB|Br|\$|€|£)\b", potential_sender, re.IGNORECASE):
                continue
                
            # Clean up common noise
            cleaned = re.sub(r"\s+(via|get|download).*$", "", potential_sender, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"\s+\d+.*$", "", cleaned).strip()
            
            # Final validation: must still look like a name
            if re.match(r"^[A-Za-z][A-Za-z\s'.-]{1,50}$", cleaned) and len(cleaned) >= 2:
                return cleaned
    
    return None


def extract_fields(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"bank": "Dashen Bank"}

    lower = text.lower()
    anchor_idx = -1
    for a in SUCCESS_ANCHORS:
        idx = lower.find(a.lower())
        if idx != -1:
            anchor_idx = idx
            break

    # Amount: Use the robust amount extraction
    amount_value = None
    if anchor_idx != -1:
        amount_value = _largest_non_fee_amount_near_anchor(text, anchor_idx)
    if amount_value is None:
        all_cands = number_candidates(text)
        if all_cands:
            amount_value = max(all_cands)
    if amount_value is not None:
        data["amount"] = amount_value
        data["amount_confidence"] = to_confidence(True)

    # Sender: Use the robust sender extraction
    sender = _extract_sender_name_robust(text)
    if sender:
        data["sender"] = sender
        data["sender_confidence"] = to_confidence(True)

    # Time: Multiple patterns for date/time
    time_str = extract_first([
        r"Date\s*[:\-]?\s*([0-3]?\d[\-/][0-1]?\d[\-/](?:\d{2}|\d{4})\s+[0-2]?\d:[0-5]\d(?::[0-5]\d)?(?:\s*(?:AM|PM))?)",
        r"Time\s*[:\-]?\s*([0-2]?\d:[0-5]\d(?::[0-5]\d)?(?:\s*(?:AM|PM))?)",
        r"Date\s*[:\-]?\s*(\d{4}[\-/]\d{1,2}[\-/]\d{1,2}(?:\s+[0-2]?\d:[0-5]\d(?::[0-5]\d)?)?)",
        r"Date\s*[:\-]?\s*([0-3]?\d[\-/][0-1]?\d[\-/]\d{2,4})",
        r"(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}\s+[0-2]?\d:[0-5]\d)",
    ], text)
    if time_str:
        data["time"] = time_str
        data["time_confidence"] = to_confidence(True)

    # Reference: Strict patterns to avoid capturing "Transaction" literally
    ft_ref = extract_first([
        r"FT\s*Ref\s*[:\-]?\s*([A-Z0-9]{6,})",
        r"Transaction\s*ID\s*[:\-]?\s*([A-Z0-9]{6,})",
        r"Ref(?:erence)?\s*(?:No\.?|#)?\s*[:\-]?\s*([A-Z0-9]{6,})",
    ], text)
    if ft_ref and ft_ref.lower() not in ["transaction", "id", "no"]:
        data["reference"] = ft_ref
        data["reference_confidence"] = to_confidence(True)

    return data
