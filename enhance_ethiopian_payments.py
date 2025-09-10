#!/usr/bin/env python3
"""
Enhance OCR to handle multiple Ethiopian mobile payment formats
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the extract_receipt_data function with comprehensive Ethiopian payment support
old_function = '''def extract_receipt_data(text):
    """Extract data from Commercial Bank of Ethiopia receipt text"""
    try:
        # Initialize result
        result = {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'time': '',
            'payer': '',
            'receiver': '',
            'bank_name': 'CBE',
            'payment_method': 'Bank Transfer',
            'currency': 'ETB'
        }
        
        # Amount patterns
        amount_patterns = [
            r'Amount[:\s]+(\d+(?:\.\d{2})?)',
            r'Total[:\s]+(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*ETB',
            r'(\d+(?:\.\d{2})?)\s*Birr',
            r'(\d+(?:\.\d{2})?)\s*USD'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['amount'] = float(match.group(1))
                break
        
        # Transaction ID patterns
        transaction_patterns = [
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Reference[:\s]+([A-Z0-9]+)',
            r'Transaction[:\s]+([A-Z0-9]+)',
            r'TXN[:\s]+([A-Z0-9]+)',
            r'FT([A-Z0-9]+)'
        ]
        
        for pattern in transaction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Date patterns
        date_patterns = [
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['date'] = match.group(1)
                break
        
        # Time patterns
        time_patterns = [
            r'Time[:\s]+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['time'] = match.group(1)
                break
        
        # Bank name patterns
        bank_patterns = [
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Awash Bank)',
            r'(Dashen Bank)',
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
            r'(Moyee Bank)',
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
        
        for pattern in bank_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['bank_name'] = match.group(1)
                break
        
        # Payment method patterns
        payment_method_patterns = [
            r'(Bank Transfer)',
            r'(Mobile Banking)',
            r'(Internet Banking)',
            r'(ATM)',
            r'(POS)',
            r'(Card Payment)',
            r'(Cash)',
            r'(Cheque)',
            r'(Wire Transfer)',
            r'(SWIFT)',
            r'(Telebirr)',
            r'(Chapa)',
            r'(Hellocash)',
            r'(Amole)',
            r'(Kacha)',
            r'(M-Birr)',
            r'(CBE Birr)',
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Awash Bank)',
            r'(Dashen Bank)',
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
        
        # Payer patterns
        payer_patterns = [
            r'From[:\s]+([A-Za-z\s]+)',
            r'Payer[:\s]+([A-Za-z\s]+)',
            r'Customer[:\s]+([A-Za-z\s]+)',
            r'Account[:\s]+([A-Za-z\s]+)',
            r'Name[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Receiver patterns
        receiver_patterns = [
            r'To[:\s]+([A-Za-z\s]+)',
            r'Receiver[:\s]+([A-Za-z\s]+)',
            r'Merchant[:\s]+([A-Za-z\s]+)',
            r'Beneficiary[:\s]+([A-Za-z\s]+)',
            r'Payee[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['receiver'] = match.group(1).strip()
                break
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting receipt data: {e}")
        return {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'time': '',
            'payer': '',
            'receiver': '',
            'bank_name': 'CBE',
            'payment_method': 'Bank Transfer',
            'currency': 'ETB'
        }'''

new_function = '''def extract_receipt_data(text):
    """Extract data from Ethiopian mobile payment receipts (CBE, Telebirr, Dashen, Abyssinia, Awash, etc.)"""
    try:
        # Initialize result
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
        
        # Enhanced amount patterns for Ethiopian mobile payments
        amount_patterns = [
            # CBE patterns
            r'Amount[:\s]+(\d+(?:\.\d{2})?)',
            r'Total[:\s]+(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*ETB',
            r'(\d+(?:\.\d{2})?)\s*Birr',
            r'(\d+(?:\.\d{2})?)\s*USD',
            # Telebirr patterns
            r'Balance[:\s]+(\d+(?:\.\d{2})?)',
            r'Paid[:\s]+(\d+(?:\.\d{2})?)',
            r'Transfer[:\s]+(\d+(?:\.\d{2})?)',
            # General patterns
            r'(\d+(?:\.\d{2})?)\s*[Bb]irr',
            r'(\d+(?:\.\d{2})?)\s*[Ee]thiopian',
            r'(\d+(?:\.\d{2})?)\s*[Cc]urrency'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['amount'] = float(match.group(1))
                break
        
        # Enhanced transaction ID patterns for all Ethiopian mobile payments
        transaction_patterns = [
            # CBE patterns
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Reference[:\s]+([A-Z0-9]+)',
            r'Transaction[:\s]+([A-Z0-9]+)',
            r'TXN[:\s]+([A-Z0-9]+)',
            r'FT([A-Z0-9]+)',
            # Telebirr patterns
            r'ID[:\s]+([A-Z0-9]+)',
            r'Code[:\s]+([A-Z0-9]+)',
            r'Receipt[:\s]+([A-Z0-9]+)',
            # Dashen patterns
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Trace[:\s]+([A-Z0-9]+)',
            # Abyssinia patterns
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Serial[:\s]+([A-Z0-9]+)',
            # Awash patterns
            r'Ref[:\s]+([A-Z0-9]+)',
            r'Batch[:\s]+([A-Z0-9]+)',
            # General patterns
            r'([A-Z0-9]{8,})',  # Generic 8+ character alphanumeric
            r'([0-9]{10,})'     # Generic 10+ digit number
        ]
        
        for pattern in transaction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
                break
        
        # Enhanced date patterns
        date_patterns = [
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})',
            r'(\d{1,2}\s+[A-Za-z]+\s+\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['date'] = match.group(1)
                break
        
        # Enhanced time patterns
        time_patterns = [
            r'Time[:\s]+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)',
            r'(\d{1,2}:\d{2})',
            r'(\d{1,2}:\d{2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['time'] = match.group(1)
                break
        
        # Enhanced bank name patterns for all Ethiopian banks
        bank_patterns = [
            # Major Ethiopian banks
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Telebirr)',
            r'(Dashen Bank)',
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
            # Mobile payment providers
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
        
        # Enhanced payment method patterns
        payment_method_patterns = [
            # Mobile payments
            r'(Telebirr)',
            r'(Mobile Banking)',
            r'(CBE Birr)',
            r'(Chapa)',
            r'(Hellocash)',
            r'(Amole)',
            r'(Kacha)',
            r'(M-Birr)',
            # Traditional banking
            r'(Bank Transfer)',
            r'(Internet Banking)',
            r'(ATM)',
            r'(POS)',
            r'(Card Payment)',
            r'(Cash)',
            r'(Cheque)',
            r'(Wire Transfer)',
            r'(SWIFT)',
            # Bank names as payment methods
            r'(Commercial Bank of Ethiopia)',
            r'(CBE)',
            r'(Awash Bank)',
            r'(Dashen Bank)',
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
        logger.error(f"Error extracting receipt data: {e}")
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
        }'''

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("OCR enhanced for all Ethiopian mobile payment formats!")
