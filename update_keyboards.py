#!/usr/bin/env python3
"""
Update keyboards to include login/logout options
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Update admin keyboard to include logout
old_admin_keyboard = '''def get_admin_keyboard(admin_id: int = None):
    """Get admin keyboard"""
    try:
        # Get pending approvals count
        pending_count = len([u for u in users.values() if not u.get('approved', False)])
        
        keyboard = {
            "inline_keyboard": [
                [{"text": f"👥 Manage Waiters ({len([u for u in users.values() if u.get('role') == 'waiter' and u.get('approved', False)])})", "callback_data": "manage_waiters"}],
                [{"text": f"⏳ Pending Approvals ({pending_count})", "callback_data": "pending_approvals"}],
                [{"text": "📊 All Transactions", "callback_data": "all_transactions"}],
                [{"text": "📥 Download Today's Report", "callback_data": "download_today"}],
                [{"text": "�� Sign Out", "callback_data": "sign_out"}]
            ]
        }
        return keyboard
    except Exception as e:
        logger.error(f"Error in get_admin_keyboard: {e}")
        return {"inline_keyboard": []}'''

new_admin_keyboard = '''def get_admin_keyboard(admin_id: int = None):
    """Get admin keyboard"""
    try:
        # Get pending approvals count
        pending_count = len([u for u in users.values() if not u.get('approved', False)])
        
        keyboard = {
            "inline_keyboard": [
                [{"text": f"👥 Manage Waiters ({len([u for u in users.values() if u.get('role') == 'waiter' and u.get('approved', False)])})", "callback_data": "manage_waiters"}],
                [{"text": f"⏳ Pending Approvals ({pending_count})", "callback_data": "pending_approvals"}],
                [{"text": "📊 All Transactions", "callback_data": "all_transactions"}],
                [{"text": "📥 Download Today's Report", "callback_data": "download_today"}],
                [{"text": "🔑 Login", "callback_data": "login"}],
                [{"text": "🚪 Sign Out", "callback_data": "sign_out"}]
            ]
        }
        return keyboard
    except Exception as e:
        logger.error(f"Error in get_admin_keyboard: {e}")
        return {"inline_keyboard": []}'''

# Replace admin keyboard
content = content.replace(old_admin_keyboard, new_admin_keyboard)

# Update waiter keyboard to include login
old_waiter_keyboard = '''def get_waiter_keyboard(waiter_id: int = None):
    """Get waiter keyboard"""
    try:
        keyboard = {
            "inline_keyboard": [
                [{"text": "💰 Capture Payment", "callback_data": "capture_payment"}],
                [{"text": "📋 My Transactions", "callback_data": "my_transactions"}],
                [{"text": "🚪 Sign Out", "callback_data": "sign_out"}]
            ]
        }
        return keyboard
    except Exception as e:
        logger.error(f"Error in get_waiter_keyboard: {e}")
        return {"inline_keyboard": []}'''

new_waiter_keyboard = '''def get_waiter_keyboard(waiter_id: int = None):
    """Get waiter keyboard"""
    try:
        keyboard = {
            "inline_keyboard": [
                [{"text": "💰 Capture Payment", "callback_data": "capture_payment"}],
                [{"text": "📋 My Transactions", "callback_data": "my_transactions"}],
                [{"text": "🔑 Login", "callback_data": "login"}],
                [{"text": "🚪 Sign Out", "callback_data": "sign_out"}]
            ]
        }
        return keyboard
    except Exception as e:
        logger.error(f"Error in get_waiter_keyboard: {e}")
        return {"inline_keyboard": []}'''

# Replace waiter keyboard
content = content.replace(old_waiter_keyboard, new_waiter_keyboard)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Keyboards updated with login options!")
