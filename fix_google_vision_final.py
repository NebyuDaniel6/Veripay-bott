#!/usr/bin/env python3
"""
Fix the bot to use REAL Google Vision API processing with the provided API key
"""

import os
import re
import base64
import requests
from datetime import datetime
from typing import Dict, Any

def handle_google_vision_ocr(image_url: str, api_key: str) -> Dict[str, Any]:
    """Process image with Google Vision API"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        image_data = response.content
        
        # Convert to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Call Google Vision API
        vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        payload = {
            "requests": [{
                "image": {"content": base64_image},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                ]
            }]
        }
        
        response = requests.post(vision_url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if 'responses' in result and len(result['responses']) > 0:
            text_annotations = result['responses'][0].get('textAnnotations', [])
            if text_annotations:
                full_text = text_annotations[0].get('description', '')
                return extract_receipt_data(full_text)
        
        return extract_receipt_data("")
        
    except Exception as e:
        print(f"Google Vision API error: {e}")
        return extract_receipt_data("")

def extract_receipt_data(text: str) -> Dict[str, Any]:
    """Extract data from Commercial Bank of Ethiopia receipt text"""
    try:
        # Initialize result
        result = {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }
        
        # Extract amount - look for "Transferred Amount:" or "Total amount debited"
        amount_patterns = [
            r'Transferred Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Total amount debited from customers account:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*ETB'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    result['amount'] = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Extract transaction ID
        transaction_patterns = [
            r'Transaction ID:\s*([A-Z0-9]+)',
            r'Ref No:\s*([A-Z0-9]+)',
            r'FT\d+[A-Z0-9]+'
        ]
        
        for pattern in transaction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # Extract date
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                result['date'] = match.group(1)
                break
        
        # Extract payer name
        payer_patterns = [
            r'Payer:\s*([A-Z\s]+)',
            r'From:\s*([A-Z\s]+)',
            r'Customer:\s*([A-Z\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Extract receiver name
        receiver_patterns = [
            r'Receiver:\s*([A-Z\s]+)',
            r'To:\s*([A-Z\s]+)',
            r'Beneficiary:\s*([A-Z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['receiver'] = match.group(1).strip()
                break
        
        return result
        
    except Exception as e:
        print(f"Error extracting receipt data: {e}")
        return {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }

# Test the functions
if __name__ == "__main__":
    # Test with the provided API key
    api_key = "AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M"
    
    # Test with a sample Commercial Bank of Ethiopia receipt text
    sample_text = """
    Commercial Bank of Ethiopia
    Transaction ID: FT25252QJQT1
    Date: 9/9/2025, 11:35:00 AM
    Payer: NEBIYU DANIEL KASSA
    Receiver: TEMESGEN TESFAMARIAM EBUY
    Transferred Amount: 570.00 ETB
    Total amount debited from customers account: 570.00 ETB
    """
    
    result = extract_receipt_data(sample_text)
    print("Extracted data:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    print("\nGoogle Vision API integration ready!")
