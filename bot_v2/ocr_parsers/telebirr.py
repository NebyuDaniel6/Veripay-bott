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
    
    # Transaction Number patterns - look for alphanumeric codes
    transaction_patterns = [
        r"Transaction\s+Number[:\s]+([A-Z0-9]{8,12})",  # Transaction Number: CHC85K0LMU
        r"Transaction\s+ID[:\s]+([A-Z0-9]{8,12})",      # Transaction ID: CHC85K0LMU
        r"Ref(?:erence)?\s+No[:\s]+([A-Z0-9]{8,12})",   # Ref No: CHC85K0LMU
        r"([A-Z0-9]{8,12})",                            # Just the code itself
    ]
    
    for pattern in transaction_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["transaction_id"] = match.group(1)
            break
    
    # Recipient/Sender patterns - look for "Transaction To"
    recipient_patterns = [
        r"Transaction\s+To[:\s]+([A-Za-z\s]+)",         # Transaction To: Mekonen
        r"To[:\s]+([A-Za-z\s]+)",                       # To: Mekonen
        r"Recipient[:\s]+([A-Za-z\s]+)",                # Recipient: Mekonen
    ]
    
    for pattern in recipient_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["sender"] = match.group(1).strip()
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
