"""
Telebirr-specific OCR parser
Handles the exact format shown in Telebirr mobile app screenshots
"""
import re
from typing import Dict, Any

def parse(text: str) -> Dict[str, Any]:
    """Parse Telebirr transaction screenshot text"""
    data = {
        "bank": "Telebirr",
        "amount": "Unknown",
        "transaction_id": "Unknown", 
        "sender": "Unknown",
        "time": "Unknown"
    }
    
    # Amount patterns - look for negative amounts with ETB
    amount_patterns = [
        r"-([0-9,]+(?:\.[0-9]{2})?)\s*\(ETB\)",  # -7,008.00 (ETB)
        r"-([0-9,]+(?:\.[0-9]{2})?)\s*ETB",       # -7,008.00 ETB
        r"([0-9,]+(?:\.[0-9]{2})?)\s*\(ETB\)",    # 7,008.00 (ETB)
        r"([0-9,]+(?:\.[0-9]{2})?)\s*ETB",        # 7,008.00 ETB
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            data["amount"] = match.group(1).replace(',', '')
            break
    
    # Transaction Number patterns - be more specific
    transaction_patterns = [
        r"Transaction\s+Number\s*[:\s]*\n?\s*(CH[A-Z0-9O]{7,})",
        r"Transaction\s+ID\s*[:\s]*\n?\s*(CH[A-Z0-9O]{7,})",
        r"Ref(?:erence)?\s+No\s*[:\s]*\n?\s*(CH[A-Z0-9O]{7,})",
        r"\bCH[A-Z0-9O]{7,}\b",
    ]
    
    for pattern in transaction_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["transaction_id"] = match.group(1)
            break
    
    # Recipient/Sender patterns - be more specific and handle OCR variations
    recipient_patterns = [
        r"Transaction\s+To\s*[:\s]*\n?\s*([A-Za-z][A-Za-z .'-]{0,40}?)(?=\s*$|\s*\n|\s*Transaction|\s*Number)",
        r"To\s*[:\s]*\n?\s*([A-Za-z][A-Za-z .'-]{0,40}?)(?=\s*$|\s*\n|\s*Transaction)",
        r"Recipient\s*[:\s]*\n?\s*([A-Za-z][A-Za-z .'-]{0,40}?)(?=\s*$|\s*\n|\s*Transaction)",
    ]
    
    for pattern in recipient_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out common OCR errors
            if name not in ['Transaction', 'Number', 'Type', 'Time', 'Download', 'Share']:
                data["sender"] = name
                break
    
    # Time patterns - look for timestamp format
    time_patterns = [
        r"Transaction\s+Time[:\s]+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})",  # 2025/08/12 13:23:22
        r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})",                          # 2025/08/12 13:23:22
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",                          # 2025-08-12 13:23:22
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            data["time"] = match.group(1)
            break
    
    return data
