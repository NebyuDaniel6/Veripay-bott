#!/usr/bin/env python3
"""
Enhanced OCR extraction for Ethiopian mobile payments
Handles Dashen Bank, Telebirr, and CBE formats
"""

import re
from datetime import datetime

def extract_receipt_data(text):
    """Enhanced extraction for Ethiopian mobile payments"""
    try:
        result = {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'time': '',
            'payer': '',
            'receiver': '',
            'bank_name': 'Unknown',
            'payment_method': 'Mobile Payment',
            'currency': 'ETB'
        }
        
        # Enhanced amount patterns for all Ethiopian mobile payments
        amount_patterns = [
            # Dashen Bank patterns
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*\(ETB\)',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*ETB',
            
            # Telebirr patterns (with negative sign)
            r'-(\d{1,3}(?:,\d{3})*\.?\d*)\s*\(ETB\)',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*\(ETB\)',
            
            # CBE patterns
            r'ETB\s*(\d{1,3}(?:,\d{3})*\.?\d*)',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*debited',
            r'Total Amount Debited\s*ETB\s*(\d{1,3}(?:,\d{3})*\.?\d*)',
            
            # General patterns
            r'Transferred Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Total amount debited from customers account:\s*([0-9,]+\.?\d*)\s*ETB',
            r'Amount:\s*([0-9,]+\.?\d*)\s*ETB',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*Birr',
            r'(\d{1,3}(?:,\d{3})*\.?\d*)\s*USD'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                result['amount'] = float(amount_str)
                break
        
        # Enhanced transaction ID patterns for all formats
        id_patterns = [
            # Dashen Bank patterns
            r'FT Ref:\s*([A-Z0-9]+)',
            r'Transaction Ref:\s*([A-Z0-9]+)',
            
            # Telebirr patterns
            r'Transaction Number:\s*([A-Z0-9]+)',
            r'Transaction ID:\s*([A-Z0-9]+)',
            
            # CBE patterns
            r'transaction ID:\s*([A-Z0-9]+)',
            r'FT\s*([A-Z0-9]+)',
            
            # General patterns
            r'VAT Invoice No[:\s]*([A-Z0-9]+)',
            r'Reference No[:\s]*\(VAT Invoice No\)[:\s]*([A-Z0-9]+)',
            r'VAT Receipt No[:\s]*([A-Z0-9]+)',
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Reference[:\s]+([A-Z0-9]+)',
            r'Transaction[:\s]+([A-Z0-9]+)',
            r'TXN[:\s]+([A-Z0-9]+)',
            r'ID[:\s]+([A-Z0-9]+)',
            r'Code[:\s]+([A-Z0-9]+)',
            r'Receipt[:\s]+([A-Z0-9]+)',
            r'Trace[:\s]+([A-Z0-9]+)',
            r'Serial[:\s]+([A-Z0-9]+)',
            r'Batch[:\s]+([A-Z0-9]+)',
            r'([A-Z0-9]{8,})',
            r'([0-9]{10,})'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Enhanced date patterns for all formats
        date_patterns = [
            # Dashen Bank patterns
            r'Date:\s*(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)',
            r'(\w{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)',
            
            # Telebirr patterns
            r'Transaction Time:\s*(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})',
            
            # CBE patterns
            r'on\s+(\d{2}-\w{3}-\d{4})',
            r'(\d{2}-\w{3}-\d{4})',
            
            # General patterns
            r'Payment Date & Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
            r'Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    result['date'] = f"{match.group(1)} {match.group(2)}"
                else:
                    result['date'] = match.group(1)
                break
        
        # Enhanced time patterns
        time_patterns = [
            r'Time:\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}:\d{2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['time'] = match.group(1)
                break
        
        # Enhanced bank name detection
        bank_patterns = [
            r'(Dashen Bank)',
            r'(Telebirr)',
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Bank of Abyssinia)',
            r'(Awash Bank)',
            r'(Nib Bank)',
            r'(Zemen Bank)',
            r'(Hibret Bank)',
            r'(Wegagen Bank)',
            r'(United Bank)',
            r'(Berhan Bank)',
            r'(Addis International Bank)',
            r'(Enat Bank)',
            r'(Lion Bank)',
            r'(Shabelle Bank)',
            r'(Siinqee Bank)',
            r'(Tsehay Bank)',
            r'(ZamZam Bank)',
            r'(Goh Betoch Bank)',
            r'(Amhara Bank)',
            r'(Rift Valley Bank)',
            r'(Oromia Bank)',
            r'(Bunna Bank)',
            r'(Ethiopian Bank)',
            r'(Hijra Bank)',
            r'(Moyee Bank)',
            r'(Chapa)',
            r'(Hellocash)',
            r'(Amole)',
            r'(Kacha)',
            r'(M-Birr)',
            r'(CBE Birr)'
        ]
        
        for pattern in bank_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['bank_name'] = match.group(1)
                break
        
        # Enhanced payment method detection
        payment_method_patterns = [
            r'(Telebirr)',
            r'(Mobile Banking)',
            r'(CBE Birr)',
            r'(Chapa)',
            r'(Hellocash)',
            r'(Amole)',
            r'(Kacha)',
            r'(M-Birr)',
            r'(Bank Transfer)',
            r'(Internet Banking)',
            r'(ATM)',
            r'(POS)',
            r'(Card Payment)',
            r'(Cash)',
            r'(Cheque)',
            r'(Wire Transfer)',
            r'(SWIFT)',
            r'(Transfer Money)',
            r'(Money Transfer)',
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Dashen Bank)',
            r'(Awash Bank)',
            r'(Bank of Abyssinia)',
            r'(Nib Bank)',
            r'(Zemen Bank)',
            r'(Hibret Bank)',
            r'(Wegagen Bank)',
            r'(United Bank)',
            r'(Berhan Bank)',
            r'(Addis International Bank)',
            r'(Enat Bank)',
            r'(Lion Bank)',
            r'(Shabelle Bank)',
            r'(Siinqee Bank)',
            r'(Tsehay Bank)',
            r'(ZamZam Bank)',
            r'(Goh Betoch Bank)',
            r'(Amhara Bank)',
            r'(Rift Valley Bank)',
            r'(Oromia Bank)',
            r'(Bunna Bank)',
            r'(Ethiopian Bank)',
            r'(Hijra Bank)',
            r'(Moyee Bank)'
        ]
        
        for pattern in payment_method_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payment_method'] = match.group(1)
                break
        
        # Enhanced payer patterns
        payer_patterns = [
            # Dashen Bank patterns
            r'Sender Name:\s*([A-Za-z\s]+)',
            r'from\s+([A-Za-z\s]+)',
            
            # Telebirr patterns
            r'Transaction To:\s*([A-Za-z\s]+)',
            r'to\s+([A-Za-z\s]+)',
            
            # CBE patterns
            r'debited from\s+([A-Za-z\s/]+)',
            r'for\s+([A-Za-z\s-]+)',
            
            # General patterns
            r'Payer[:\s]*([A-Z\s]+)',
            r'Customer Name[:\s]*([A-Z\s]+)',
            r'From[:\s]+([A-Za-z\s]+)',
            r'Payer[:\s]+([A-Za-z\s]+)',
            r'Customer[:\s]+([A-Za-z\s]+)',
            r'Account[:\s]+([A-Za-z\s]+)',
            r'Name[:\s]+([A-Za-z\s]+)',
            r'Sender[:\s]+([A-Za-z\s]+)',
            r'User[:\s]+([A-Za-z\s]+)',
            r'Phone[:\s]+([0-9\s]+)',
            r'Mobile[:\s]+([0-9\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Enhanced receiver patterns
        receiver_patterns = [
            # Dashen Bank patterns
            r'Recipient Name:\s*([A-Za-z\s]+)',
            r'to\s+([A-Za-z\s]+)',
            
            # Telebirr patterns
            r'Transaction To:\s*([A-Za-z\s]+)',
            r'to\s+([A-Za-z\s]+)',
            
            # CBE patterns
            r'for\s+([A-Za-z\s-]+)',
            r'to\s+([A-Za-z\s-]+)',
            
            # General patterns
            r'Receiver[:\s]*([A-Z\s]+)',
            r'Payee[:\s]*([A-Z\s]+)',
            r'To[:\s]+([A-Za-z\s]+)',
            r'Receiver[:\s]+([A-Za-z\s]+)',
            r'Merchant[:\s]+([A-Za-z\s]+)',
            r'Beneficiary[:\s]+([A-Za-z\s]+)',
            r'Payee[:\s]+([A-Za-z\s]+)',
            r'Recipient[:\s]+([A-Za-z\s]+)',
            r'Destination[:\s]+([A-Za-z\s]+)',
            r'Business[:\s]+([A-Za-z\s]+)',
            r'Restaurant[:\s]+([A-Za-z\s]+)',
            r'Store[:\s]+([A-Za-z\s]+)'
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
            'time': '',
            'payer': '',
            'receiver': '',
            'bank_name': 'Unknown',
            'payment_method': 'Mobile Payment',
            'currency': 'ETB'
        }

# Test with sample data
if __name__ == "__main__":
    # Test Dashen Bank format
    dashen_text = """
    Money Successfully Sent!
    10,000.00 (ETB)
    Sender Name: Mariamawit Alemayehu Zewdu
    Recipient Name: Meseret Ayalew
    Date: Aug 08, 2025 01:07 PM
    FT Ref: 264OBTS2522001Yo
    Transaction Ref: OBTS08022286760791946435
    Dashen Bank
    """
    
    # Test Telebirr format
    telebirr_text = """
    Successful
    -7,008.00 (ETB)
    Transaction Time: 2025/08/12 13:23:22
    Transaction Type: Transfer Money
    Transaction To: Mekonen
    Transaction Number: CHC85K0LMU
    Telebirr
    """
    
    # Test CBE format
    cbe_text = """
    Thank you Success
    ETB 10,000.00 debited from MARAMAWIT ALEMAYEHU/ YEBEHIR DIGITA for NEBIYU DANIEL KASSA-ETB-0389 on 06-Sep-2025 with transaction ID: FT25249P26RL.
    Total Amount Debited ETB 10000 with commission of ETB 0 and 15% VAT of ETB0.00.
    Commercial Bank of Ethiopia
    """
    
    print("=== DASHEN BANK TEST ===")
    dashen_result = extract_receipt_data(dashen_text)
    print(f"Amount: {dashen_result['amount']}")
    print(f"Transaction ID: {dashen_result['transaction_id']}")
    print(f"Date: {dashen_result['date']}")
    print(f"Bank: {dashen_result['bank_name']}")
    print(f"Payer: {dashen_result['payer']}")
    print(f"Receiver: {dashen_result['receiver']}")
    
    print("\n=== TELEBIRR TEST ===")
    telebirr_result = extract_receipt_data(telebirr_text)
    print(f"Amount: {telebirr_result['amount']}")
    print(f"Transaction ID: {telebirr_result['transaction_id']}")
    print(f"Date: {telebirr_result['date']}")
    print(f"Bank: {telebirr_result['bank_name']}")
    print(f"Payer: {telebirr_result['payer']}")
    print(f"Receiver: {telebirr_result['receiver']}")
    
    print("\n=== CBE TEST ===")
    cbe_result = extract_receipt_data(cbe_text)
    print(f"Amount: {cbe_result['amount']}")
    print(f"Transaction ID: {cbe_result['transaction_id']}")
    print(f"Date: {cbe_result['date']}")
    print(f"Bank: {cbe_result['bank_name']}")
    print(f"Payer: {cbe_result['payer']}")
    print(f"Receiver: {cbe_result['receiver']}")
