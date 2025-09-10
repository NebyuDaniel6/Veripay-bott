#!/usr/bin/env python3
"""
Update photo handling to display enhanced OCR data
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the confirmation message in handle_photo_message
old_confirmation = '''            # Send confirmation
            message = f"✅ Payment captured!\nTransaction ID: {transaction_id}\nAmount: {ocr_data['currency']} {ocr_data['amount']:.2f}"
            if ocr_data["transaction_id"]:
                message += f"\nOriginal Ref: {ocr_data['transaction_id']}"
            if ocr_data["payer"]:
                message += f"\nPayer: {ocr_data['payer']}"
            
            send_message(chat_id, message, get_waiter_keyboard(user_id))'''

new_confirmation = '''            # Send confirmation
            message = f"✅ Payment captured!\n\n"
            message += f"Transaction ID: {transaction_id}\n"
            message += f"Amount: {ocr_data['currency']} {ocr_data['amount']:.2f}\n"
            message += f"Bank: {ocr_data.get('bank_name', 'CBE')}\n"
            message += f"Payment Method: {ocr_data.get('payment_method', 'Bank Transfer')}\n"
            
            if ocr_data.get("transaction_id"):
                message += f"Original Ref: {ocr_data['transaction_id']}\n"
            if ocr_data.get("date"):
                message += f"Date: {ocr_data['date']}\n"
            if ocr_data.get("time"):
                message += f"Time: {ocr_data['time']}\n"
            if ocr_data.get("payer"):
                message += f"Payer: {ocr_data['payer']}\n"
            if ocr_data.get("receiver"):
                message += f"Receiver: {ocr_data['receiver']}\n"
            
            send_message(chat_id, message, get_waiter_keyboard(user_id))'''

# Replace the confirmation message
content = content.replace(old_confirmation, new_confirmation)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Photo display updated with enhanced OCR data!")
