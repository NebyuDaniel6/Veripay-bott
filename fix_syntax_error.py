#!/usr/bin/env python3
"""
Fix syntax error in the bot file
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and remove the leftover code
old_code = """            
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing receipt. Please try again.")
            
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
                confirmation_text = f"✅ Payment captured!\n\n"
                confirmation_text += f"Transaction ID: {transaction_id}\n"
                confirmation_text += f"Amount: {amount:.2f} {currency}\n"
                confirmation_text += f"Bank: {bank}\n"
                confirmation_text += f"Payer: {receipt_data.get('payer', 'Unknown')}\n"
                confirmation_text += f"Receiver: {receipt_data.get('receiver', 'Unknown')}"
            else:
                confirmation_text = f"✅ Payment captured!\nTransaction ID: {transaction_id}\nAmount: {amount:.2f} {currency}"
            
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
            send_message(chat_id, f"✅ Payment captured!\nTransaction ID: {transaction_id}\nAmount: {amount:.2f} USD", get_waiter_keyboard(user_id))"""

new_code = """            
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing receipt. Please try again.")"""

# Replace the code
content = content.replace(old_code, new_code)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Syntax error fixed!")
