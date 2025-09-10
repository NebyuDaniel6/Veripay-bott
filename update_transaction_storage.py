#!/usr/bin/env python3
"""
Update transaction storage to include all extracted OCR data
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the transaction creation in handle_photo_message
old_transaction = '''            # Create transaction record
            transaction = {
                'id': transaction_id,
                'waiter_id': waiter_ids.get(user_id, 'N/A'),
                'amount': ocr_data['amount'],
                'currency': ocr_data['currency'],
                'status': 'completed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'date': datetime.now().strftime('%Y-%m-%d')
            }'''

new_transaction = '''            # Create transaction record with all extracted data
            transaction = {
                'id': transaction_id,
                'waiter_id': waiter_ids.get(user_id, 'N/A'),
                'amount': ocr_data['amount'],
                'currency': ocr_data['currency'],
                'bank': ocr_data.get('bank_name', 'Unknown'),
                'payment_method': ocr_data.get('payment_method', 'Mobile Payment'),
                'date': ocr_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'time': ocr_data.get('time', datetime.now().strftime('%H:%M:%S')),
                'payer': ocr_data.get('payer', 'Unknown'),
                'receiver': ocr_data.get('receiver', 'Unknown'),
                'original_ref': ocr_data.get('transaction_id', ''),
                'status': 'completed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }'''

# Replace the transaction creation
content = content.replace(old_transaction, new_transaction)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Transaction storage updated with all extracted OCR data!")
