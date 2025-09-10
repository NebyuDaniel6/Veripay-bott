#!/usr/bin/env python3
"""
Completely fix the photo handling function to use REAL Google Vision API
"""

import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find the current photo handling function and replace it completely
old_function = '''def handle_photo_message(chat_id, user_id, photo):
    """Handle photo messages (receipt processing)"""
    try:
        if user_states.get(user_id) != UserState.CAPTURING_PAYMENT:
            send_message(chat_id, "Please use the menu to capture payment. / እባክዎ ክፍያ ለማስቀመጥ የምናሌን ይጠቀሙ።")
            return
        
        # Get the largest photo size
        if not photo:
            send_message(chat_id, "No photo received. Please try again. / ፎቶ አልተቀበለም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        # Get the largest photo
        largest_photo = max(photo, key=lambda x: x.get('file_size', 0))
        file_id = largest_photo.get('file_id')
        
        if not file_id:
            send_message(chat_id, "Invalid photo. Please try again. / የማይሰራ ፎቶ። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        # Get file info
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10)
        
        if file_response.status_code != 200:
            send_message(chat_id, "Failed to process photo. Please try again. / ፎቶ ማስተካከል አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        file_data = file_response.json()
        if not file_data.get('ok'):
            send_message(chat_id, "Failed to process photo. Please try again. / ፎቶ ማስተካከል አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
            return
        
        file_path = file_data['result']['file_path']
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Download and process photo with REAL OCR
        try:
            # Download the actual photo
            photo_response = requests.get(photo_url, timeout=30)
            if photo_response.status_code != 200:
                send_message(chat_id, "Failed to download photo. Please try again. / ፎቶ ማውረድ አልተሳካም። እባክዎ እንደገና ይሞክሩ።", get_waiter_keyboard(user_id))
                return
            
            # For now, we'll simulate OCR by using the known CBE receipt data
            # In production, you would use Google Vision API or Tesseract OCR here
            # Since we know this is a CBE receipt from your upload, we'll use the real data
            real_ocr_text = """
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
            
            # Process the receipt with REAL data
            receipt_data = process_cbe_receipt(real_ocr_text)'''

new_function = '''def handle_photo_message(chat_id, user_id, photo):
    """Handle photo messages for receipt processing"""
    try:
        if user_states.get(user_id) != UserState.CAPTURING_PAYMENT:
            send_message(chat_id, "Please use the menu to capture payment. / እባክዎ ክፍያ ለማስቀመጥ የምናሌን ይጠቀሙ።")
            return
        
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
                'waiter_id': waiter_ids.get(user_id, 'N/A'),
                'amount': ocr_data['amount'],
                'currency': ocr_data['currency'],
                'timestamp': datetime.now().isoformat(),
                'ocr_data': ocr_data,
                'status': 'completed'
            }
            
            # Store transaction
            if user_id not in transactions:
                transactions[user_id] = []
            transactions[user_id].append(transaction)
            
            # Add to admin transactions
            user_data = users.get(user_id, {})
            restaurant_name = user_data.get('restaurant_name', '')
            if restaurant_name:
                if restaurant_name not in admin_transactions:
                    admin_transactions[restaurant_name] = []
                admin_transactions[restaurant_name].append(transaction)
            
            # Reset state
            user_states[user_id] = UserState.IDLE
            
            # Send confirmation
            message = f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {ocr_data['currency']} {ocr_data['amount']:.2f}"
            if ocr_data['transaction_id']:
                message += f"\\nOriginal Ref: {ocr_data['transaction_id']}"
            if ocr_data['payer']:
                message += f"\\nPayer: {ocr_data['payer']}"
            
            send_message(chat_id, message, get_waiter_keyboard(user_id))
        else:
            send_message(chat_id, "❌ Could not extract payment information from receipt. Please ensure the receipt is clear and try again.")
            
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing receipt. Please try again.")'''

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Photo handling function completely fixed to use REAL Google Vision API!")
