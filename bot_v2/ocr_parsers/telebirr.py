"""
Telebirr-specific OCR parser - DO NOT MODIFY WITHOUT UPDATING TESTS
This parser handles Telebirr mobile app screenshots with deterministic rules.
Protected by comprehensive test suite in tests/test_telebirr_parser.py
"""
import re
from typing import Dict, Any

def parse(text: str) -> Dict[str, Any]:
    """
    Parse Telebirr transaction screenshot text with deterministic rules.
    
    Returns:
        Dict with keys: bank, amount, transaction_id, sender, time
    """
    data = {
        "bank": "Telebirr",
        "amount": "Unknown",
        "transaction_id": "Unknown", 
        "sender": "Unknown",
        "time": "Unknown"
    }
    
    # Amount patterns - handle negative amounts and various formats
    amount_patterns = [
        r"-([0-9,]+(?:\.[0-9]{2})?)\s*(?:\(ETB\)|ETB)",  # -7,008.00 (ETB) or -7,008.00 ETB
        r"([0-9,]+(?:\.[0-9]{2})?)\s*(?:\(ETB\)|ETB)",   # 7,008.00 (ETB) or 7,008.00 ETB
        r"Amount\s*[:#-]?\s*(?:\r?\n)?\s*([0-9,]+(?:\.[0-9]{2})?)\s*(?:ETB|Birr)?",  # Amount: 7,008.00
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Remove commas and normalize
            amount = match.group(1).replace(',', '')
            data["amount"] = amount
            break
    
    # Transaction Number patterns - prioritize CH codes, handle same/next line
    transaction_patterns = [
        r"Transaction\s+Number\s*[:#-]?\s*(?:\r?\n)?\s*(CH[A-Z0-9O]{7,})",  # Transaction Number: CHC85K0LMU
        r"Transaction\s+ID\s*[:#-]?\s*(?:\r?\n)?\s*(CH[A-Z0-9O]{7,})",      # Transaction ID: CHC85K0LMU
        r"Ref(?:erence)?\s+No\s*[:#-]?\s*(?:\r?\n)?\s*(CH[A-Z0-9O]{7,})",   # Ref No: CHC85K0LMU
        r"\b(CH[A-Z0-9O]{7,})\b",                                             # Bare CH code with capture group
    ]
    
    for pattern in transaction_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Normalize: keep as-is, don't convert O to 0 automatically
            data["transaction_id"] = match.group(1)
            break
    
    # Recipient/Sender patterns - handle "Transaction To" format
    # Special handling for the messy OCR format: "Transaction To: Transaction Number: 2025/08/12 13:23:22 Transfer Money Mekonen"
    recipient_patterns = [
        # Look for "Transfer Money" followed by a name (common pattern in Telebirr)
        r"Transfer\s+Money\s+([A-Za-z][A-Za-z .\'-]{1,40}?)(?=\s+CH|\s*$|\s*\n)",
        # Standard patterns
        r"Transaction\s+To\s*[:#-]?\s*(?:\r?\n)?\s*([A-Za-z][A-Za-z .\'-]{1,40}?)(?=\s*$|\s*\n|\s*Transaction|\s*Number|\s*Time|\s*Amount)",  # Transaction To: Mekonen
        r"To\s*[:#-]?\s*(?:\r?\n)?\s*([A-Za-z][A-Za-z .\'-]{1,40}?)(?=\s*$|\s*\n|\s*Transaction|\s*Number|\s*Time|\s*Amount)",             # To: Mekonen
        r"Recipient\s*[:#-]?\s*(?:\r?\n)?\s*([A-Za-z][A-Za-z .\'-]{1,40}?)(?=\s*$|\s*\n|\s*Transaction|\s*Number|\s*Time|\s*Amount)",        # Recipient: Mekonen
    ]
    
    # Noise words to filter out
    noise_words = {
        'transaction', 'number', 'download', 'share', 'money', 'transfer', 
        'type', 'time', 'amount', 'successful', 'finished', 'qr', 'code',
        'receive', 'abroad', 'via', 'telebirr', 'visa', 'thunes', 'onafriq',
        'gift', 'send', 'dahabshill'
    }
    
    for pattern in recipient_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out noise words
            if name.lower() not in noise_words and len(name) > 1:
                data["sender"] = name
                break
    
    # Time patterns - handle various timestamp formats
    time_patterns = [
        r"Transaction\s+Time\s*[:#-]?\s*(?:\r?\n)?\s*(\d{4}[/-]\d{2}[/-]\d{2}\s+\d{2}:\d{2}:\d{2})",  # Transaction Time: 2025/08/12 13:23:22
        r"Time\s*[:#-]?\s*(?:\r?\n)?\s*(\d{4}[/-]\d{2}[/-]\d{2}\s+\d{2}:\d{2}:\d{2})",                # Time: 2025/08/12 13:23:22
        r"(\d{4}[/-]\d{2}[/-]\d{2}\s+\d{2}:\d{2}:\d{2})",                                            # Bare timestamp
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            data["time"] = match.group(1)
            break
    
    return data
