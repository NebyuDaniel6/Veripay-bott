#!/usr/bin/env python3
"""
Update the bot to use REAL Google Vision API processing
"""

import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Add the Google Vision API key at the top
api_key_line = 'GOOGLE_VISION_API_KEY = "AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M"\n\n'
if 'GOOGLE_VISION_API_KEY' not in content:
    content = api_key_line + content

# Add the Google Vision functions
google_vision_functions = '''
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
            r'Transferred Amount:\\s*([0-9,]+\.?\\d*)\\s*ETB',
            r'Total amount debited from customers account:\\s*([0-9,]+\.?\\d*)\\s*ETB',
            r'Amount:\\s*([0-9,]+\.?\\d*)\\s*ETB',
            r'(\\d{1,3}(?:,\\d{3})*\\.?\\d*)\\s*ETB'
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
            r'Transaction ID:\\s*([A-Z0-9]+)',
            r'Ref No:\\s*([A-Z0-9]+)',
            r'FT\\d+[A-Z0-9]+'
        ]
        
        for pattern in transaction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # Extract date
        date_patterns = [
            r'(\\d{1,2}/\\d{1,2}/\\d{4})',
            r'(\\d{4}-\\d{2}-\\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                result['date'] = match.group(1)
                break
        
        # Extract payer name
        payer_patterns = [
            r'Payer:\\s*([A-Z\\s]+)',
            r'From:\\s*([A-Z\\s]+)',
            r'Customer:\\s*([A-Z\\s]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['payer'] = match.group(1).strip()
                break
        
        # Extract receiver name
        receiver_patterns = [
            r'Receiver:\\s*([A-Z\\s]+)',
            r'To:\\s*([A-Z\\s]+)',
            r'Beneficiary:\\s*([A-Z\\s]+)'
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

'''

# Add the functions after the existing functions
if 'def handle_google_vision_ocr' not in content:
    # Find a good place to insert the functions
    insert_point = content.find('def handle_photo_message')
    if insert_point != -1:
        content = content[:insert_point] + google_vision_functions + content[insert_point:]

# Update the photo handling function to use real OCR
old_photo_function = '''def handle_photo_message(chat_id: int, user_id: int, photo: dict):
    """Handle photo messages for receipt processing"""
    try:
        # Get the largest photo size
        photo_sizes = photo.get('photo', [])
        if not photo_sizes:
            send_message(chat_id, "❌ No photo found. Please try again.")
            return
        
        largest_photo = max(photo_sizes, key=lambda x: x.get('width', 0) * x.get('height', 0))
        file_id = largest_photo.get('file_id')
        
        if not file_id:
            send_message(chat_id, "❌ Could not process photo. Please try again.")
            return
        
        # Get file path from Telegram
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(file_url)
        
        if response.status_code != 200:
            send_message(chat_id, "❌ Could not download photo. Please try again.")
            return
        
        file_data = response.json()
        if not file_data.get('ok'):
            send_message(chat_id, "❌ Could not access photo. Please try again.")
            return
        
        file_path = file_data['result']['file_path']
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Process with Google Vision API
        api_key = os.getenv('GOOGLE_VISION_API_KEY', '')
        if not api_key:
            # Fallback to mock data if no API key
            mock_ocr_text = """
            Commercial Bank of Ethiopia
            Transaction ID: FT25252QJQT1
            Date: 9/9/2025, 11:35:00 AM
            Payer: NEBIYU DANIEL KASSA
            Receiver: TEMESGEN TESFAMARIAM EBUY
            Transferred Amount: 570.00 ETB
            Total amount debited from customers account: 570.00 ETB
            """
            ocr_data = extract_receipt_data(mock_ocr_text)
        else:
            ocr_data = handle_google_vision_ocr(image_url, api_key)
        
        if ocr_data['amount'] > 0:
            # Generate transaction ID
            transaction_id = f"TXN{random.randint(10000000, 99999999):X}"
            
            # Create transaction
            transaction = {
                'id': transaction_id,
                'waiter_id': user_states.get(user_id, {}).get('waiter_id', 'Unknown'),
                'amount': ocr_data['amount'],
                'currency': ocr_data['currency'],
                'timestamp': datetime.now().isoformat(),
                'ocr_data': ocr_data,
                'status': 'completed'
            }
            
            # Store transaction
            if 'transactions' not in user_states:
                user_states['transactions'] = []
            user_states['transactions'].append(transaction)
            
            # Send confirmation
            message = f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {ocr_data['currency']} {ocr_data['amount']:.2f}"
            if ocr_data['transaction_id']:
                message += f"\\nOriginal Ref: {ocr_data['transaction_id']}"
            if ocr_data['payer']:
                message += f"\\nPayer: {ocr_data['payer']}"
            
            send_message(chat_id, message)
            
            # Update waiter keyboard
            keyboard = get_waiter_keyboard(user_id)
            send_message(chat_id, "What would you like to do next?", reply_markup=keyboard)
        else:
            send_message(chat_id, "❌ Could not extract payment information from receipt. Please ensure the receipt is clear and try again.")
            
    except Exception as e:
        print(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing receipt. Please try again.")'''

new_photo_function = '''def handle_photo_message(chat_id: int, user_id: int, photo: dict):
    """Handle photo messages for receipt processing"""
    try:
        # Get the largest photo size
        photo_sizes = photo.get('photo', [])
        if not photo_sizes:
            send_message(chat_id, "❌ No photo found. Please try again.")
            return
        
        largest_photo = max(photo_sizes, key=lambda x: x.get('width', 0) * x.get('height', 0))
        file_id = largest_photo.get('file_id')
        
        if not file_id:
            send_message(chat_id, "❌ Could not process photo. Please try again.")
            return
        
        # Get file path from Telegram
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(file_url)
        
        if response.status_code != 200:
            send_message(chat_id, "❌ Could not download photo. Please try again.")
            return
        
        file_data = response.json()
        if not file_data.get('ok'):
            send_message(chat_id, "❌ Could not access photo. Please try again.")
            return
        
        file_path = file_data['result']['file_path']
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Process with Google Vision API
        api_key = GOOGLE_VISION_API_KEY
        ocr_data = handle_google_vision_ocr(image_url, api_key)
        
        if ocr_data['amount'] > 0:
            # Generate transaction ID
            transaction_id = f"TXN{random.randint(10000000, 99999999):X}"
            
            # Create transaction
            transaction = {
                'id': transaction_id,
                'waiter_id': user_states.get(user_id, {}).get('waiter_id', 'Unknown'),
                'amount': ocr_data['amount'],
                'currency': ocr_data['currency'],
                'timestamp': datetime.now().isoformat(),
                'ocr_data': ocr_data,
                'status': 'completed'
            }
            
            # Store transaction
            if 'transactions' not in user_states:
                user_states['transactions'] = []
            user_states['transactions'].append(transaction)
            
            # Send confirmation
            message = f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {ocr_data['currency']} {ocr_data['amount']:.2f}"
            if ocr_data['transaction_id']:
                message += f"\\nOriginal Ref: {ocr_data['transaction_id']}"
            if ocr_data['payer']:
                message += f"\\nPayer: {ocr_data['payer']}"
            
            send_message(chat_id, message)
            
            # Update waiter keyboard
            keyboard = get_waiter_keyboard(user_id)
            send_message(chat_id, "What would you like to do next?", reply_markup=keyboard)
        else:
            send_message(chat_id, "❌ Could not extract payment information from receipt. Please ensure the receipt is clear and try again.")
            
    except Exception as e:
        print(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing receipt. Please try again.")'''

# Replace the photo handling function
content = content.replace(old_photo_function, new_photo_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Bot updated with real Google Vision API processing!")
