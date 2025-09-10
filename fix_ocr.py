#!/usr/bin/env python3
"""
Fix OCR processing for Commercial Bank of Ethiopia receipts
"""

import re
import base64
import requests
from datetime import datetime

def extract_receipt_data(text):
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
            r'Amount:\s*([0-9,]+\.?\d*)\s*ETB'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                result['amount'] = float(amount_str)
                break
        
        # Extract transaction ID - look for "VAT Invoice No" or "Reference No"
        id_patterns = [
            r'VAT Invoice No[:\s]*([A-Z0-9]+)',
            r'Reference No[:\s]*\(VAT Invoice No\)[:\s]*([A-Z0-9]+)',
            r'VAT Receipt No[:\s]*([A-Z0-9]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Extract date - look for "Payment Date & Time"
        date_patterns = [
            r'Payment Date & Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
            r'Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    result['date'] = f"{match.group(1)} {match.group(2)}"
                else:
                    result['date'] = match.group(1)
                break
        
        # Extract payer name
        payer_patterns = [
            r'Payer[:\s]*([A-Z\s]+)',
            r'Customer Name[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Extract receiver name
        receiver_patterns = [
            r'Receiver[:\s]*([A-Z\s]+)',
            r'Payee[:\s]*([A-Z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['receiver'] = match.group(1).strip()
                break
        
        return result
        
    except Exception as e:
        print(f"Error extracting receipt data: {e}")
        return None

def process_cbe_receipt(text):
    """Process Commercial Bank of Ethiopia receipt specifically"""
    try:
        # Check if this is a CBE receipt
        if 'Commercial Bank of Ethiopia' not in text and 'CBE' not in text:
            return None
        
        data = extract_receipt_data(text)
        if data and data['amount'] > 0:
            return {
                'amount': data['amount'],
                'currency': data['currency'],
                'transaction_id': data['transaction_id'] or f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'date': data['date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'payer': data['payer'] or 'Unknown',
                'receiver': data['receiver'] or 'Unknown',
                'bank': 'Commercial Bank of Ethiopia',
                'status': 'completed'
            }
        
        return None
        
    except Exception as e:
        print(f"Error processing CBE receipt: {e}")
        return None

# Test with sample text
if __name__ == "__main__":
    sample_text = """
    Commercial Bank of Ethiopia
    VAT Invoice / Customer Receipt
    
    Customer Name: NEBIYU DANIEL KASSA
    Payer: NEBIYU DANIEL KASSA
    Receiver: TEMESGEN TESFAMARIAM EBUY
    Payment Date & Time: 9/9/2025, 11:35:00 AM
    Reference No. (VAT Invoice No): FT25252QJQT1
    Transferred Amount: 570.00 ETB
    Total amount debited from customers account: 570.00 ETB
    """
    
    result = process_cbe_receipt(sample_text)
    print("Extracted data:", result)
