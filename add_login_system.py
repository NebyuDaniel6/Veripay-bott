#!/usr/bin/env python3
"""
Add login system for approved users
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Add login state to UserState class
old_userstate = '''class UserState:
    IDLE = "idle"
    REGISTERING_WAITER = "registering_waiter"
    REGISTERING_ADMIN = "registering_admin"
    WAITING_NAME = "waiting_name"
    WAITING_PHONE = "waiting_phone"
    WAITING_RESTAURANT = "waiting_restaurant"
    CAPTURING_PAYMENT = "capturing_payment"'''

new_userstate = '''class UserState:
    IDLE = "idle"
    REGISTERING_WAITER = "registering_waiter"
    REGISTERING_ADMIN = "registering_admin"
    WAITING_NAME = "waiting_name"
    WAITING_PHONE = "waiting_phone"
    WAITING_RESTAURANT = "waiting_restaurant"
    CAPTURING_PAYMENT = "capturing_payment"
    LOGGING_IN = "logging_in"'''

# Replace UserState
content = content.replace(old_userstate, new_userstate)

# Add login functions after the existing functions
login_functions = '''

def handle_login(chat_id, user_id):
    """Handle user login"""
    try:
        user_data = users.get(user_id, {})
        if user_data.get('approved', False):
            # User is already approved, show appropriate menu
            if user_data.get('role') == 'admin':
                send_message(chat_id, f"Welcome back, {user_data.get('name', 'Admin')}! / እንኳን ደህና መጡ።", get_admin_keyboard(user_id))
            else:
                send_message(chat_id, f"Welcome back, {user_data.get('name', 'Waiter')}! / እንኳን ደህና መጡ።", get_waiter_keyboard(user_id))
        else:
            # User not approved yet
            send_message(chat_id, "You are not approved yet. Please wait for admin approval. / እስካሁን አልተፀድቁም። እባክዎ የአስተዳዳሪውን ፀድቆ ይጠብቁ።")
    except Exception as e:
        logger.error(f"Error in handle_login: {e}")

def check_user_login(user_id):
    """Check if user is logged in and approved"""
    user_data = users.get(user_id, {})
    return user_data.get('approved', False)

def get_user_role(user_id):
    """Get user role"""
    user_data = users.get(user_id, {})
    return user_data.get('role', 'unknown')

def auto_login_user(chat_id, user_id, first_name, last_name):
    """Auto-login user if they are approved"""
    try:
        user_data = users.get(user_id, {})
        if user_data.get('approved', False):
            # User is approved, show appropriate menu
            if user_data.get('role') == 'admin':
                send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_admin_keyboard(user_id))
            else:
                send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_waiter_keyboard(user_id))
            return True
        return False
    except Exception as e:
        logger.error(f"Error in auto_login_user: {e}")
        return False'''

# Add login functions before the main function
content = content.replace('def main():', login_functions + '\ndef main():')

# Update the start command to include login option
old_start = '''def handle_start(chat_id, user_id, first_name, last_name):
    """Handle /start command"""
    try:
        # Check if user is already registered
        if user_id in users:
            user_data = users[user_id]
            if user_data.get('approved', False):
                if user_data.get('role') == 'admin':
                    send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_admin_keyboard(user_id))
                else:
                    send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_waiter_keyboard(user_id))
            else:
                send_message(chat_id, "Your registration is pending approval. / የእርስዎ ምዝገባ ፀድቆ እየተጠበቀ ነው።")
        else:
            # New user - show registration options
            welcome_text = f"🎉 Welcome to VeriPay! / ወደ VeriPay እንኳን ደህና መጡ!\n\nHello {first_name}! 👋 ሰላም {first_name}! 👋\n\nVeriPay helps restaurants manage payments and transactions efficiently.\nVeriPay ምግብ ቤቶች ክፍያዎችን እና ግብይቶችን በብቃት እንዲያስተዳድሩ ይረዳል።\n\nPlease select your role: / እባክዎ ሚናዎን ይምረጡ:"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "👨‍💼 Register as Admin / አስተዳዳሪ ሆነው ይመዝገቡ", "callback_data": "register_admin"}],
                    [{"text": "👨‍🍳 Register as Waiter / ወጣት ሆነው ይመዝገቡ", "callback_data": "register_waiter"}]
                ]
            }
            
            send_message(chat_id, welcome_text, keyboard)
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")'''

new_start = '''def handle_start(chat_id, user_id, first_name, last_name):
    """Handle /start command"""
    try:
        # Check if user is already registered
        if user_id in users:
            user_data = users[user_id]
            if user_data.get('approved', False):
                if user_data.get('role') == 'admin':
                    send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_admin_keyboard(user_id))
                else:
                    send_message(chat_id, f"Welcome back, {user_data.get('name', first_name)}! / እንኳን ደህና መጡ።", get_waiter_keyboard(user_id))
            else:
                send_message(chat_id, "Your registration is pending approval. / የእርስዎ ምዝገባ ፀድቆ እየተጠበቀ ነው።")
        else:
            # New user - show registration options
            welcome_text = f"🎉 Welcome to VeriPay! / ወደ VeriPay እንኳን ደህና መጡ!\n\nHello {first_name}! 👋 ሰላም {first_name}! 👋\n\nVeriPay helps restaurants manage payments and transactions efficiently.\nVeriPay ምግብ ቤቶች ክፍያዎችን እና ግብይቶችን በብቃት እንዲያስተዳድሩ ይረዳል።\n\nPlease select your role: / እባክዎ ሚናዎን ይምረጡ:"
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "👨‍💼 Register as Admin / አስተዳዳሪ ሆነው ይመዝገቡ", "callback_data": "register_admin"}],
                    [{"text": "👨‍🍳 Register as Waiter / ወጣት ሆነው ይመዝገቡ", "callback_data": "register_waiter"}],
                    [{"text": "🔑 Login / ይግቡ", "callback_data": "login"}]
                ]
            }
            
            send_message(chat_id, welcome_text, keyboard)
    except Exception as e:
        logger.error(f"Error in handle_start: {e}")'''

# Replace the start function
content = content.replace(old_start, new_start)

# Add login callback handler
old_callback = '''    elif callback_data == "main_menu":
        handle_main_menu(chat_id, user_id)'''

new_callback = '''    elif callback_data == "main_menu":
        handle_main_menu(chat_id, user_id)
    elif callback_data == "login":
        handle_login(chat_id, user_id)'''

# Replace the callback handler
content = content.replace(old_callback, new_callback)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Login system added!")
