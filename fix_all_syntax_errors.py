#!/usr/bin/env python3
"""
Fix all syntax errors in the bot
"""
import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Fix all unterminated strings
fixes = [
    ('await query.edit_message_text("📊 **My Transactions**\n\nNo transactions recorded yet.")', 
     'await query.edit_message_text("📊 **My Transactions**\\n\\nNo transactions recorded yet.")'),
    
    ('message = f"📊 **My Transactions**\n\n"', 
     'message = f"📊 **My Transactions**\\n\\n"'),
    
    ('message += f"**Waiter ID:** {waiter_id}\n"', 
     'message += f"**Waiter ID:** {waiter_id}\\n"'),
    
    ('message += f"**Total Transactions:** {len(waiter_transactions)}\n\n"', 
     'message += f"**Total Transactions:** {len(waiter_transactions)}\\n\\n"'),
    
    ('message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"', 
     'message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\\n"'),
    
    ('message += f"  Payer: {txn.payer} | Date: {txn.date}\n\n"', 
     'message += f"  Payer: {txn.payer} | Date: {txn.date}\\n\\n"'),
    
    ('message += f"... and {len(waiter_transactions) - 10} more transactions"', 
     'message += f"... and {len(waiter_transactions) - 10} more transactions"'),
]

# Apply all fixes
for old, new in fixes:
    content = content.replace(old, new)

# Write the fixed content back
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("✅ All syntax errors fixed!")
