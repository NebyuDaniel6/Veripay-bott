#!/usr/bin/env python3
"""
Fix the photo handling function to use REAL Google Vision API processing
"""

import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the photo handling function
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
        
        # Process with OCR
        real_ocr_text = process_receipt_with_ocr(image_url)
        receipt_data = process_cbe_receipt(real_ocr_text)
        
        if not receipt_data:
            # Fallback to mock data if OCR fails
            transaction_id = f"TXN{str(uuid.uuid4())[:8].upper()}"
            amount = 25.50
            currency = "USD"
            bank = "Unknown Bank"
        else:
            transaction_id = receipt_data['transaction_id']
            amount = receipt_data['amount']
            currency = receipt_data['currency']
            bank = receipt_data['bank']
        
        # Create transaction
        transaction = {
            'id': transaction_id,
            'waiter_id': waiter_ids.get(user_id, 'N/A'),
            'amount': amount,
            'currency': currency,
            'bank': bank,
            'status': 'completed',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'payer': receipt_data.get('payer', 'Unknown') if receipt_data else 'Unknown',
            'receiver': receipt_data.get('receiver', 'Unknown') if receipt_data else 'Unknown'
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
        
        # Send confirmation with real data
        if receipt_data:
            confirmation_text = f"✅ Payment captured!\\n\\n"
            confirmation_text += f"Transaction ID: {transaction_id}\\n"
            confirmation_text += f"Amount: {amount:.2f} {currency}\\n"
            confirmation_text += f"Bank: {bank}\\n"
            confirmation_text += f"Payer: {receipt_data.get('payer', 'Unknown')}\\n"
            confirmation_text += f"Receiver: {receipt_data.get('receiver', 'Unknown')}"
        else:
            confirmation_text = f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {amount:.2f} {currency}"
        
        send_message(chat_id, confirmation_text, get_waiter_keyboard(user_id))
        
    except Exception as e:
        logger.error(f"Error processing photo with OCR: {e}")
        # Fallback to mock data
        transaction_id = f"TXN{str(uuid.uuid4())[:8].upper()}"
        amount = 25.50
        
        transaction = {
            'id': transaction_id,
            'waiter_id': waiter_ids.get(user_id, 'N/A'),
            'amount': amount,
            'status': 'completed',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        if user_id not in transactions:
            transactions[user_id] = []
        transactions[user_id].append(transaction)
        
        user_states[user_id] = UserState.IDLE
        send_message(chat_id, f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {amount:.2f} USD", get_waiter_keyboard(user_id))'''

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

# Replace the photo handling function
content = content.replace(old_photo_function, new_photo_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Photo handling function updated to use REAL Google Vision API processing!")
