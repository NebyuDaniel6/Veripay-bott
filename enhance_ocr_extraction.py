#!/usr/bin/env python3
"""
Enhance OCR extraction to get date, time, and bank name
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the extract_receipt_data function
old_function = '''def extract_receipt_data(text):
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
        
        # Amount patterns
        amount_patterns = [
            r'Amount[:\s]+(\d+(?:\.\d{2})?)',
            r'Total[:\s]+(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?)\s*ETB',
            r'(\d+(?:\.\d{2})?)\s*Birr'
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
            r'TXN[:\s]+([A-Z0-9]+)'
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
        
        # Payer patterns
        payer_patterns = [
            r'From[:\s]+([A-Za-z\s]+)',
            r'Payer[:\s]+([A-Za-z\s]+)',
            r'Customer[:\s]+([A-Za-z\s]+)'
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
            r'Merchant[:\s]+([A-Za-z\s]+)'
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
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }'''

new_function = '''def extract_receipt_data(text):
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

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("OCR extraction enhanced with date, time, and bank name!")
