#!/usr/bin/env python3
"""
Add Google Vision API support to the bot
"""

import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Add Google Vision functions after the existing functions
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
        
        response = requests.post(vision_url, json=payload, timeout=10)
        result = response.json()
        
        if "responses" in result and result["responses"]:
            response_data = result["responses"][0]
            text_annotations = response_data.get("textAnnotations", [])
            full_text = text_annotations[0].get("description", "") if text_annotations else ""
            
            return {
                "full_text": full_text,
                "confidence": 0.8,
                "processed_at": datetime.now().isoformat()
            }
        
        return {
            "full_text": "No text detected",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing image with Google Vision: {e}")
        return {
            "full_text": "Error processing image",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }

def extract_receipt_data_from_google_vision(text: str) -> Dict[str, Any]:
    """Extract data from Commercial Bank of Ethiopia receipt text using Google Vision"""
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
            r'([0-9,]+\.?\\d*)\\s*ETB'
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
            r'Ref\\.\\s*([A-Z0-9]+)',
            r'([A-Z0-9]{10,})'
        ]
        
        for pattern in transaction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['transaction_id'] = match.group(1)
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
        logger.error(f"Error extracting receipt data: {e}")
        return {
            'amount': 0.0,
            'transaction_id': '',
            'date': '',
            'payer': '',
            'receiver': '',
            'currency': 'ETB'
        }
'''

# Find where to insert the functions (before handle_photo_message)
insertion_point = content.find('def handle_photo_message(chat_id, user_id, photo):')
if insertion_point == -1:
    print("Could not find insertion point")
    exit(1)

# Insert the Google Vision functions before handle_photo_message
new_content = content[:insertion_point] + google_vision_functions + '\n' + content[insertion_point:]

# Update the handle_photo_message function to use Google Vision API
old_photo_function = '''def handle_photo_message(chat_id, user_id, photo):
    """Handle photo upload for payment capture"""
    session = user_sessions.get(user_id, {})
    user = users.get(user_id)
    
    if not user or not user["approved"]:
        send_message(chat_id, "❌ You need to be approved first!")
        return
    
    try:
        # Get photo file
        file_id = photo["file_id"]
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10)
        file_data = file_response.json()
        
        if not file_data["ok"]:
            send_message(chat_id, "❌ Error getting photo file")
            return
        
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_data['result']['file_path']}"
        
        # In production, you would use Google Vision API or Tesseract OCR here
        # For now, we'll use mock data
        mock_ocr_text = """
        Commercial Bank of Ethiopia
        Transfer Receipt
        
        Transaction ID: FT25252QJQT1
        Date: 9/9/2025, 11:35:00 AM
        
        Payer: NEBIYU DANIEL KASSA
        Receiver: TEMESGEN TESFAMARIAM EBUY
        
        Transferred Amount: 570.00 ETB
        Total amount debited from customers account: 570.00 ETB
        
        Thank you for using CBE services!
        """
        
        # Extract data from OCR text
        receipt_data = extract_receipt_data(mock_ocr_text)
        
        # Create transaction
        transaction = {
            "id": f"TXN{int(time.time())}",
            "user_id": user_id,
            "waiter_id": user["waiter_id"],
            "amount": receipt_data["amount"],
            "currency": receipt_data["currency"],
            "transaction_id": receipt_data["transaction_id"],
            "date": receipt_data["date"],
            "payer": receipt_data["payer"],
            "receiver": receipt_data["receiver"],
            "ocr_status": "Processed",
            "timestamp": datetime.now().isoformat()
        }
        
        # Store transaction
        transactions[transaction["id"]] = transaction
        
        # Send confirmation
        message = f"""✅ Payment captured! Transaction ID: {transaction["id"]}
Amount: ${transaction["amount"]:.2f} {transaction["currency"]}
Payer: {transaction["payer"]}
Receiver: {transaction["receiver"]}
Date: {transaction["date"]}"""
        
        send_message(chat_id, message)
        
        # Send waiter keyboard
        keyboard = get_waiter_keyboard(user_id)
        send_message(chat_id, "What would you like to do next?", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        send_message(chat_id, "❌ Error processing photo. Please try again.")'''

new_photo_function = '''def handle_photo_message(chat_id, user_id, photo):
    """Handle photo upload for payment capture"""
    session = user_sessions.get(user_id, {})
    user = users.get(user_id)
    
    if not user or not user["approved"]:
        send_message(chat_id, "❌ You need to be approved first!")
        return
    
    try:
        # Get photo file
        file_id = photo["file_id"]
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10)
        file_data = file_response.json()
        
        if not file_data["ok"]:
            send_message(chat_id, "❌ Error getting photo file")
            return
        
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_data['result']['file_path']}"
        
        # Process with Google Vision API if available, otherwise use mock data
        if GOOGLE_VISION_API_KEY:
            logger.info("Processing image with Google Vision API")
            ocr_result = handle_google_vision_ocr(photo_url, GOOGLE_VISION_API_KEY)
            receipt_data = extract_receipt_data_from_google_vision(ocr_result["full_text"])
        else:
            logger.info("Google Vision API key not available, using mock data")
            # Use mock data for testing
            mock_ocr_text = """
            Commercial Bank of Ethiopia
            Transfer Receipt
            
            Transaction ID: FT25252QJQT1
            Date: 9/9/2025, 11:35:00 AM
            
            Payer: NEBIYU DANIEL KASSA
            Receiver: TEMESGEN TESFAMARIAM EBUY
            
            Transferred Amount: 570.00 ETB
            Total amount debited from customers account: 570.00 ETB
            
            Thank you for using CBE services!
            """
            receipt_data = extract_receipt_data(mock_ocr_text)
        
        # Create transaction
        transaction = {
            "id": f"TXN{int(time.time())}",
            "user_id": user_id,
            "waiter_id": user["waiter_id"],
            "amount": receipt_data["amount"],
            "currency": receipt_data["currency"],
            "transaction_id": receipt_data["transaction_id"],
            "date": receipt_data["date"],
            "payer": receipt_data["payer"],
            "receiver": receipt_data["receiver"],
            "ocr_status": "Processed" if GOOGLE_VISION_API_KEY else "Mock Data",
            "timestamp": datetime.now().isoformat()
        }
        
        # Store transaction
        transactions[transaction["id"]] = transaction
        
        # Send confirmation
        message = f"""✅ Payment captured! Transaction ID: {transaction["id"]}
Amount: {transaction["amount"]:.2f} {transaction["currency"]}
Payer: {transaction["payer"]}
Receiver: {transaction["receiver"]}
Date: {transaction["date"]}
OCR Status: {transaction["ocr_status"]}"""
        
        send_message(chat_id, message)
        
        # Send waiter keyboard
        keyboard = get_waiter_keyboard(user_id)
        send_message(chat_id, "What would you like to do next?", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        send_message(chat_id, "❌ Error processing photo. Please try again.")'''

# Replace the old photo function with the new one
new_content = new_content.replace(old_photo_function, new_photo_function)

# Write the updated bot file
with open('veripay_bot.py', 'w') as f:
    f.write(new_content)

print("Bot updated with Google Vision API support!")
print("The bot will now:")
print("1. Use Google Vision API if GOOGLE_VISION_API_KEY is set")
print("2. Fall back to mock data if no API key is available")
print("3. Process real Commercial Bank of Ethiopia receipts")
