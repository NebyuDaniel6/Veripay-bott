#!/usr/bin/env python3
"""
Create a completely working bot with REAL Google Vision API
"""

# Read the backup file
with open('veripay_bot_backup_broken.py', 'r') as f:
    content = f.read()

# Find and remove the broken photo function completely
lines = content.split('\n')
new_lines = []
skip_until_next_def = False

for i, line in enumerate(lines):
    if line.strip().startswith('def handle_photo_message'):
        skip_until_next_def = True
        # Add the correct photo function
        new_lines.append('def handle_photo_message(chat_id, user_id, photo):')
        new_lines.append('    """Handle photo messages for receipt processing"""')
        new_lines.append('    try:')
        new_lines.append('        if user_states.get(user_id) != UserState.CAPTURING_PAYMENT:')
        new_lines.append('            send_message(chat_id, "Please use the menu to capture payment. / እባክዎ ክፍያ ለማስቀመጥ የምናሌን ይጠቀሙ።")')
        new_lines.append('            return')
        new_lines.append('        ')
        new_lines.append('        # Get the largest photo size')
        new_lines.append('        photo_sizes = photo.get("photo", [])')
        new_lines.append('        if not photo_sizes:')
        new_lines.append('            send_message(chat_id, "❌ No photo found. Please try again.")')
        new_lines.append('            return')
        new_lines.append('        ')
        new_lines.append('        largest_photo = max(photo_sizes, key=lambda x: x.get("width", 0) * x.get("height", 0))')
        new_lines.append('        file_id = largest_photo.get("file_id")')
        new_lines.append('        ')
        new_lines.append('        if not file_id:')
        new_lines.append('            send_message(chat_id, "❌ Could not process photo. Please try again.")')
        new_lines.append('            return')
        new_lines.append('        ')
        new_lines.append('        # Get file path from Telegram')
        new_lines.append('        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"')
        new_lines.append('        response = requests.get(file_url)')
        new_lines.append('        ')
        new_lines.append('        if response.status_code != 200:')
        new_lines.append('            send_message(chat_id, "❌ Could not download photo. Please try again.")')
        new_lines.append('            return')
        new_lines.append('        ')
        new_lines.append('        file_data = response.json()')
        new_lines.append('        if not file_data.get("ok"):')
        new_lines.append('            send_message(chat_id, "❌ Could not access photo. Please try again.")')
        new_lines.append('            return')
        new_lines.append('        ')
        new_lines.append('        file_path = file_data["result"]["file_path"]')
        new_lines.append('        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"')
        new_lines.append('        ')
        new_lines.append('        # Process with Google Vision API')
        new_lines.append('        api_key = GOOGLE_VISION_API_KEY')
        new_lines.append('        ocr_data = handle_google_vision_ocr(image_url, api_key)')
        new_lines.append('        ')
        new_lines.append('        if ocr_data["amount"] > 0:')
        new_lines.append('            # Generate transaction ID')
        new_lines.append('            transaction_id = f"TXN{random.randint(10000000, 99999999):X}"')
        new_lines.append('            ')
        new_lines.append('            # Create transaction')
        new_lines.append('            transaction = {')
        new_lines.append('                "id": transaction_id,')
        new_lines.append('                "waiter_id": waiter_ids.get(user_id, "N/A"),')
        new_lines.append('                "amount": ocr_data["amount"],')
        new_lines.append('                "currency": ocr_data["currency"],')
        new_lines.append('                "timestamp": datetime.now().isoformat(),')
        new_lines.append('                "ocr_data": ocr_data,')
        new_lines.append('                "status": "completed"')
        new_lines.append('            }')
        new_lines.append('            ')
        new_lines.append('            # Store transaction')
        new_lines.append('            if user_id not in transactions:')
        new_lines.append('                transactions[user_id] = []')
        new_lines.append('            transactions[user_id].append(transaction)')
        new_lines.append('            ')
        new_lines.append('            # Add to admin transactions')
        new_lines.append('            user_data = users.get(user_id, {})')
        new_lines.append('            restaurant_name = user_data.get("restaurant_name", "")')
        new_lines.append('            if restaurant_name:')
        new_lines.append('                if restaurant_name not in admin_transactions:')
        new_lines.append('                    admin_transactions[restaurant_name] = []')
        new_lines.append('                admin_transactions[restaurant_name].append(transaction)')
        new_lines.append('            ')
        new_lines.append('            # Reset state')
        new_lines.append('            user_states[user_id] = UserState.IDLE')
        new_lines.append('            ')
        new_lines.append('            # Send confirmation')
        new_lines.append('            message = f"✅ Payment captured!\\nTransaction ID: {transaction_id}\\nAmount: {ocr_data[\'currency\']} {ocr_data[\'amount\']:.2f}"')
        new_lines.append('            if ocr_data["transaction_id"]:')
        new_lines.append('                message += f"\\nOriginal Ref: {ocr_data[\'transaction_id\']}"')
        new_lines.append('            if ocr_data["payer"]:')
        new_lines.append('                message += f"\\nPayer: {ocr_data[\'payer\']}"')
        new_lines.append('            ')
        new_lines.append('            send_message(chat_id, message, get_waiter_keyboard(user_id))')
        new_lines.append('        else:')
        new_lines.append('            send_message(chat_id, "❌ Could not extract payment information from receipt. Please ensure the receipt is clear and try again.")')
        new_lines.append('            ')
        new_lines.append('    except Exception as e:')
        new_lines.append('        logger.error(f"Error processing photo: {e}")')
        new_lines.append('        send_message(chat_id, "❌ Error processing receipt. Please try again.")')
        continue
    elif skip_until_next_def and line.strip().startswith('def '):
        skip_until_next_def = False
        new_lines.append(line)
    elif not skip_until_next_def:
        new_lines.append(line)

# Join the lines back
new_content = '\n'.join(new_lines)

# Write the new content
with open('veripay_bot.py', 'w') as f:
    f.write(new_content)

print("Working bot created with REAL Google Vision API!")
