#!/usr/bin/env python3
"""
Completely rewrite the photo handling function
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find the photo handling function and replace it completely
start_marker = "def handle_photo_message(chat_id, user_id, photo):"
end_marker = "def handle_"

# Find the start
start_pos = content.find(start_marker)
if start_pos == -1:
    print("Could not find photo function start")
    exit(1)

# Find the next function
next_func_pos = content.find(end_marker, start_pos + len(start_marker))
if next_func_pos == -1:
    print("Could not find next function")
    exit(1)

# Extract the old function
old_function = content[start_pos:next_func_pos]

# New function
new_function = """def handle_photo_message(chat_id, user_id, photo):
    \"\"\"Handle photo messages for receipt processing\"\"\"
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
        send_message(chat_id, "❌ Error processing receipt. Please try again.")

"""

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Photo handling function completely rewritten!")
