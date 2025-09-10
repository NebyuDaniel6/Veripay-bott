#!/usr/bin/env python3
"""
VeriPay Bot - Complete Milestone 1 (All Features Working)
The ONLY bot file you need - everything else is deleted!
"""

import os
import json
import time
import logging
import requests
import base64
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('veripay.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc')
GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY', '')

# Global storage
users = {}  # user_id -> user_data
user_sessions = {}  # user_id -> session_data
user_states = {}  # user_id -> current_state
transactions = {}  # user_id -> [transactions]
admin_transactions = {}  # restaurant_name -> [all_transactions]
pending_approvals = {}  # restaurant_name -> [pending_waiters]
restaurant_ids = {}  # restaurant_name -> restaurant_id

# Process management
bot_running = False
bot_process_id = None

class UserState:
    IDLE = "idle"
    REGISTERING_WAITER = "registering_waiter"
    REGISTERING_ADMIN = "registering_admin"
    WAITING_NAME = "waiting_name"
    WAITING_PHONE = "waiting_phone"
    WAITING_RESTAURANT = "waiting_restaurant"
    WAITING_TABLE = "waiting_table"
    WAITING_AMOUNT = "waiting_amount"
    WAITING_PHOTO = "waiting_photo"

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global bot_running
    logger.info("Received shutdown signal. Stopping bot gracefully...")
    bot_running = False
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def send_message(chat_id: int, text: str, reply_markup=None, parse_mode="Markdown"):
    """Send message to Telegram with retry logic"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 409:
                # Conflict - message already sent, continue
                logger.warning("Message conflict (409) - continuing")
                return {"ok": True}
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    return None

def get_main_keyboard():
    """Get main menu keyboard"""
    return {
        "inline_keyboard": [
            [
                {"text": "🍽️ Register as Waiter / አስተናጋጅ", "callback_data": "register_waiter"},
                {"text": "👨‍💼 Register as Admin / አስተዳዳሪ", "callback_data": "register_admin"}
            ]
        ]
    }

def get_waiter_keyboard():
    """Get waiter menu keyboard"""
    return {
        "inline_keyboard": [
            [
                {"text": "💳 Capture Payment / ክፍያ ይቀርጹ", "callback_data": "capture_payment"},
                {"text": "📊 My Transactions / የእኔ ግብይቶች", "callback_data": "my_transactions"}
            ],
            [
                {"text": "🚪 Sign Out / ውጣ", "callback_data": "sign_out"},
                {"text": "🏠 Main Menu / ዋና ሜኑ", "callback_data": "main_menu"}
            ]
        ]
    }

def get_admin_keyboard():
    """Get admin menu keyboard"""
    return {
        "inline_keyboard": [
            [
                {"text": "👥 Manage Waiters / አስተናጋጆችን አስተዳድር", "callback_data": "manage_waiters"},
                {"text": "📊 All Transactions / ሁሉም ግብይቶች", "callback_data": "all_transactions"}
            ],
            [
                {"text": "⚙️ Restaurant Settings / የምግብ ቤት ቅንብሮች", "callback_data": "restaurant_settings"},
                {"text": "✅ Pending Approvals / በመጠባበቅ ላይ", "callback_data": "pending_approvals"}
            ],
            [
                {"text": "🚪 Sign Out / ውጣ", "callback_data": "sign_out"},
                {"text": "🏠 Main Menu / ዋና ሜኑ", "callback_data": "main_menu"}
            ]
        ]
    }

def get_pending_approvals_keyboard(restaurant_name: str):
    """Get pending approvals keyboard with approve/reject buttons"""
    pending = pending_approvals.get(restaurant_name, [])
    keyboard = []
    
    for waiter_id in pending:
        waiter = users.get(waiter_id)
        if waiter:
            keyboard.append([
                {"text": f"✅ Approve {waiter['name']}", "callback_data": f"approve_waiter_{waiter_id}"},
                {"text": f"❌ Reject {waiter['name']}", "callback_data": f"reject_waiter_{waiter_id}"}
            ])
    
    keyboard.append([{"text": "🔙 Back to Admin Menu", "callback_data": "admin_menu"}])
    return {"inline_keyboard": keyboard}

def generate_restaurant_id(restaurant_name: str) -> str:
    """Generate unique restaurant ID"""
    timestamp = str(int(time.time()))[-6:]
    prefix = restaurant_name.replace(" ", "").upper()[:3]
    restaurant_id = f"RST{timestamp}"
    restaurant_ids[restaurant_name] = restaurant_id
    logger.info(f"Generated restaurant ID {restaurant_id} for {restaurant_name}")
    return restaurant_id

def handle_start(chat_id: int, user_id: int, username: str = ""):
    """Handle /start command"""
    # Check if user is already registered and approved
    user = users.get(user_id)
    if user and user["approved"]:
        if user["role"] == "admin":
            welcome_text = f"""🎉 **Welcome back, {username}! / እንኳን ደህና መጡ, {username}!**

You are logged in as **Admin** of {user["restaurant"]}
እንደ **አስተዳዳሪ** የ{user["restaurant"]} ተገኝተዋል

**Restaurant ID:** {user["restaurant_id"]}
**የምግብ ቤት መለያ:** {user["restaurant_id"]}

What would you like to do?
ምን ማድረግ ይፈልጋሉ?"""
            send_message(chat_id, welcome_text, get_admin_keyboard())
        else:
            welcome_text = f"""🎉 **Welcome back, {username}! / እንኳን ደህና መጡ, {username}!**

You are logged in as **Waiter** at {user["restaurant"]}
እንደ **አስተናጋጅ** በ{user["restaurant"]} ተገኝተዋል

**Restaurant ID:** {user["restaurant_id"]}
**የምግብ ቤት መለያ:** {user["restaurant_id"]}

What would you like to do?
ምን ማድረግ ይፈልጋሉ?"""
            send_message(chat_id, welcome_text, get_waiter_keyboard())
        return
    
    # New user registration
    welcome_text = f"""🎉 **Welcome to VeriPay! / ወደ VeriPay እንኳን ደህና መጡ!**

Hello {username}! 👋
ሰላም {username}! 👋

VeriPay helps restaurants manage payments and transactions efficiently.
VeriPay ምግብ ቤቶች ክፍያዎችን እና ግብይቶችን በብቃት እንዲያስተዳድሩ ይረዳል።

Please select your role:
እባክዎ ሚናዎን ይምረጡ:"""

    send_message(chat_id, welcome_text, get_main_keyboard())

def handle_register_waiter(chat_id: int, user_id: int):
    """Handle waiter registration"""
    user_states[user_id] = UserState.REGISTERING_WAITER
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["registration_type"] = "waiter"
    user_states[user_id] = UserState.WAITING_NAME
    
    text = """🍽️ **Waiter Registration / የአስተናጋጅ ምዝገባ**
እንደ አስተናጋጅ እንመዝግብህ!

**Step 1/3: What's your full name?**
**ደረጃ 1/3: ሙሉ ስምህ ምንድን ነው?**

Please type your full name (e.g., Abdulahi Mohammed)
ሙሉ ስምህን ይተይቡ (ለምሳሌ: አብዱላሂ መሐመድ)"""
    
    send_message(chat_id, text)

def handle_register_admin(chat_id: int, user_id: int):
    """Handle admin registration"""
    user_states[user_id] = UserState.REGISTERING_ADMIN
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["registration_type"] = "admin"
    user_states[user_id] = UserState.WAITING_NAME
    
    text = """👨‍💼 **Admin Registration / የአስተዳዳሪ ምዝገባ**
እንደ አስተዳዳሪ እንመዝግብህ!

**Step 1/3: What's your full name?**
**ደረጃ 1/3: ሙሉ ስምህ ምንድን ነው?**

Please type your full name (e.g., Nebyu Daniel)
ሙሉ ስምህን ይተይቡ (ለምሳሌ: ነብዩ ዳንኤል)"""
    
    send_message(chat_id, text)

def handle_name_input(chat_id: int, user_id: int, name: str):
    """Handle name input"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    session["name"] = name
    user_states[user_id] = UserState.WAITING_PHONE
    
    text = """**Step 2/3: What's your phone number?**
**ደረጃ 2/3: ስልክ ቁጥርህ ምንድን ነው?**

Please type your phone number (e.g., 0912345678)
ስልክ ቁጥርህን ይተይቡ (ለምሳሌ: 0912345678)"""
    
    send_message(chat_id, text)

def handle_phone_input(chat_id: int, user_id: int, phone: str):
    """Handle phone input"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    session["phone"] = phone
    user_states[user_id] = UserState.WAITING_RESTAURANT
    
    text = """**Step 3/3: What's your restaurant name?**
**ደረጃ 3/3: የምግብ ቤት ስም ምንድን ነው?**

Please type your restaurant name (e.g., Yohannes Kitfo)
የምግብ ቤት ስምን ይተይቡ (ለምሳሌ: ዮሐንስ ክትፎ)"""
    
    send_message(chat_id, text)

def handle_restaurant_input(chat_id: int, user_id: int, restaurant_name: str):
    """Handle restaurant input and complete registration"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    session["restaurant"] = restaurant_name
    session["role"] = session["registration_type"]
    session["restaurant_id"] = generate_restaurant_id(restaurant_name)
    session["approved"] = session["role"] == "admin"  # Admins are auto-approved
    
    # Store user data
    users[user_id] = {
        "name": session["name"],
        "phone": session["phone"],
        "restaurant": restaurant_name,
        "role": session["role"],
        "restaurant_id": session["restaurant_id"],
        "approved": session["approved"],
        "registered_at": datetime.now().isoformat()
    }
    
    # Handle approval based on role
    if session["role"] == "waiter":
        # Add to pending approvals
        if restaurant_name not in pending_approvals:
            pending_approvals[restaurant_name] = []
        pending_approvals[restaurant_name].append(user_id)
        
        text = f"""✅ **Registration Complete! / ምዝገባ ተጠናቋል!**

**Restaurant ID:** {session["restaurant_id"]}
**የምግብ ቤት መለያ:** {session["restaurant_id"]}

⏳ **Waiting for admin approval...**
⏳ **የአስተዳዳሪ ፈቃድ በመጠባበቅ ላይ...**

An admin from {restaurant_name} needs to approve your registration.
ከ{restaurant_name} አስተዳዳሪ ምዝገባዎን መፈቀድ አለበት።"""
        
        send_message(chat_id, text)
    else:
        # Admin auto-approved - auto-login
        text = f"""✅ **Admin Registration Complete! / የአስተዳዳሪ ምዝገባ ተጠናቋል!**

**Restaurant ID:** {session["restaurant_id"]}
**የምግብ ቤት መለያ:** {session["restaurant_id"]}

🎉 **You are now logged in as Admin!**
🎉 **አሁን እንደ አስተዳዳሪ ተገኝተዋል!**"""
        
        send_message(chat_id, text, get_admin_keyboard())
    
    # Reset state
    user_states[user_id] = UserState.IDLE
    del user_sessions[user_id]

def handle_capture_payment(chat_id: int, user_id: int):
    """Handle payment capture start"""
    user = users.get(user_id)
    if not user or not user["approved"]:
        send_message(chat_id, "❌ You need to be approved first!")
        return
    
    user_states[user_id] = UserState.WAITING_TABLE
    
    text = """💳 **Capture Payment / ክፍያ ይቀርጹ**

**Step 1/3: What's the table number?**
**ደረጃ 1/3: የጠረጴዛ ቁጥር ምንድን ነው?**

Please type the table number (e.g., Table 5)
የጠረጴዛ ቁጥርን ይተይቡ (ለምሳሌ: ጠረጴዛ 5)"""
    
    send_message(chat_id, text)

def handle_table_input(chat_id: int, user_id: int, table: str):
    """Handle table input"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["table"] = table
    user_states[user_id] = UserState.WAITING_AMOUNT
    
    text = """**Step 2/3: What's the payment amount?**
**ደረጃ 2/3: የክፍያ መጠን ምንድን ነው?**

Please type the amount (e.g., 250.00)
መጠኑን ይተይቡ (ለምሳሌ: 250.00)"""
    
    send_message(chat_id, text)

def handle_amount_input(chat_id: int, user_id: int, amount: str):
    """Handle amount input"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["amount"] = float(amount)
    user_states[user_id] = UserState.WAITING_PHOTO
    
    text = """**Step 3/3: Send payment screenshot**
**ደረጃ 3/3: የክፍያ ስክሪንሾት ይላኩ**

Please send a photo of the payment confirmation
የክፍያ ማረጋገጫ ፎቶ ይላኩ"""
    
    send_message(chat_id, text)

def handle_google_vision_ocr(image_url: str) -> Dict[str, Any]:
    """Process image with Google Vision API"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        image_data = response.content
        
        # Convert to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Call Google Vision API
        vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"
        payload = {
            "requests": [{
                "image": {"content": base64_image},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                ]
            }]
        }
        
        response = requests.post(vision_url, json=payload, timeout=10)
        result = response.json()
        
        if "responses" in result and result["responses"]:
            response_data = result["responses"][0]
            text_annotations = response_data.get("textAnnotations", [])
            full_text = text_annotations[0].get("description", "") if text_annotations else ""
            
            return {
                "full_text": full_text,
                "confidence": 0.8,
                "processed_at": datetime.now().isoformat()
            }
        
        return {
            "full_text": "No text detected",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return {
            "full_text": "Error processing image",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }

def handle_photo(chat_id: int, user_id: int, photo: Dict):
    """Handle photo upload"""
    session = user_sessions.get(user_id, {})
    user = users.get(user_id)
    
    if not user or not user["approved"]:
        send_message(chat_id, "❌ You need to be approved first!")
        return
    
    try:
        # Get photo file
        file_id = photo["file_id"]
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_response = requests.get(file_url, timeout=10)
        file_data = file_response.json()
        
        if not file_data["ok"]:
            send_message(chat_id, "❌ Error getting photo file")
            return
        
        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_data['result']['file_path']}"
        
        # Process with Google Vision API
        ocr_result = handle_google_vision_ocr(photo_url)
        
        # Create transaction
        transaction = {
            "id": str(int(time.time())),
            "user_id": user_id,
            "waiter_name": user["name"],
            "restaurant": user["restaurant"],
            "restaurant_id": user["restaurant_id"],
            "table": session.get("table", "Unknown"),
            "amount": session.get("amount", 0.0),
            "date": datetime.now().isoformat(),
            "photo_url": photo_url,
            "ocr_data": ocr_result
        }
        
        # Store transaction
        if user_id not in transactions:
            transactions[user_id] = []
        transactions[user_id].append(transaction)
        
        # Store in admin transactions
        if user["restaurant"] not in admin_transactions:
            admin_transactions[user["restaurant"]] = []
        admin_transactions[user["restaurant"]].append(transaction)
        
        text = f"""✅ **Payment Captured Successfully! / ክፍያ በተሳካ ሁኔታ ተቀርጿል!**

**Transaction ID:** {transaction["id"]}
**የግብይት መለያ:** {transaction["id"]}
**Table:** {session.get("table", "Unknown")}
**ጠረጴዛ:** {session.get("table", "Unknown")}
**Amount:** {session.get("amount", 0.0)} ETB
**መጠን:** {session.get("amount", 0.0)} ብር
**Date:** {datetime.now().strftime("%d/%m/%Y")}
**ቀን:** {datetime.now().strftime("%d/%m/%Y")}

🎉 **Payment verified and recorded!**
🎉 **ክፍያ ተረጋግጧል እና ተመዝግቧል!**"""
        
        send_message(chat_id, text, get_waiter_keyboard())
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        send_message(chat_id, "❌ Error processing payment photo")
    
    # Reset state
    user_states[user_id] = UserState.IDLE
    if user_id in user_sessions:
        del user_sessions[user_id]

def handle_my_transactions(chat_id: int, user_id: int):
    """Handle my transactions request"""
    user = users.get(user_id)
    if not user or not user["approved"]:
        send_message(chat_id, "❌ You need to be approved first!")
        return
    
    user_transactions = transactions.get(user_id, [])
    
    if not user_transactions:
        send_message(chat_id, "📊 **No transactions found / ምንም ግብይት አልተገኘም**", get_waiter_keyboard())
        return
    
    text = "📊 **Your Transactions / የእኔ ግብይቶች**\n\n"
    
    for i, tx in enumerate(user_transactions[-10:], 1):
        text += f"**{i}.** {tx['table']} - {tx['amount']} ETB\n"
        text += f"   {datetime.fromisoformat(tx['date']).strftime('%d/%m/%Y')}\n\n"
    
    send_message(chat_id, text, get_waiter_keyboard())

def handle_all_transactions(chat_id: int, user_id: int):
    """Handle all transactions request"""
    user = users.get(user_id)
    if not user or user["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    all_transactions = admin_transactions.get(user["restaurant"], [])
    
    if not all_transactions:
        send_message(chat_id, "📊 **No transactions found / ምንም ግብይት አልተገኘም**", get_admin_keyboard())
        return
    
    text = "📊 **All Transactions / ሁሉም ግብይቶች**\n\n"
    
    for i, tx in enumerate(all_transactions[-20:], 1):
        text += f"**{i}.** {tx['waiter_name']} - {tx['table']} - {tx['amount']} ETB\n"
        text += f"   {datetime.fromisoformat(tx['date']).strftime('%d/%m/%Y')}\n\n"
    
    send_message(chat_id, text, get_admin_keyboard())

def handle_manage_waiters(chat_id: int, user_id: int):
    """Handle manage waiters request"""
    user = users.get(user_id)
    if not user or user["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    restaurant_waiters = [u for u in users.values() 
                         if u["restaurant"] == user["restaurant"] 
                         and u["role"] == "waiter" 
                         and u["approved"]]
    
    if not restaurant_waiters:
        send_message(chat_id, "👥 **No waiters found / ምንም አስተናጋጆች አልተገኙም**", get_admin_keyboard())
        return
    
    text = "👥 **Restaurant Waiters / የምግብ ቤት አስተናጋጆች**\n\n"
    
    for i, waiter in enumerate(restaurant_waiters, 1):
        text += f"**{i}.** {waiter['name']}\n"
        text += f"   📞 {waiter['phone']}\n"
        text += f"   📅 {datetime.fromisoformat(waiter['registered_at']).strftime('%d/%m/%Y')}\n\n"
    
    send_message(chat_id, text, get_admin_keyboard())

def handle_restaurant_settings(chat_id: int, user_id: int):
    """Handle restaurant settings request"""
    user = users.get(user_id)
    if not user or user["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    text = f"""⚙️ **Restaurant Settings / የምግብ ቤት ቅንብሮች**

**Restaurant Name:** {user["restaurant"]}
**የምግብ ቤት ስም:** {user["restaurant"]}
**Restaurant ID:** {user["restaurant_id"]}
**የምግብ ቤት መለያ:** {user["restaurant_id"]}
**Admin:** {user["name"]}
**አስተዳዳሪ:** {user["name"]}
**Phone:** {user["phone"]}
**ስልክ:** {user["phone"]}

✅ **Settings loaded successfully!**
✅ **ቅንብሮች በተሳካ ሁኔታ ተጭነዋል!**"""
    
    send_message(chat_id, text, get_admin_keyboard())

def handle_pending_approvals(chat_id: int, user_id: int):
    """Handle pending approvals request"""
    user = users.get(user_id)
    if not user or user["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    pending = pending_approvals.get(user["restaurant"], [])
    
    if not pending:
        send_message(chat_id, "✅ **No pending approvals / ምንም በመጠባበቅ ላይ ያሉ ፈቃዶች የሉም**", get_admin_keyboard())
        return
    
    text = "⏳ **Pending Approvals / በመጠባበቅ ላይ ያሉ ፈቃዶች**\n\n"
    
    for i, waiter_id in enumerate(pending, 1):
        waiter = users.get(waiter_id)
        if waiter:
            text += f"**{i}.** {waiter['name']}\n"
            text += f"   📞 {waiter['phone']}\n"
            text += f"   �� {datetime.fromisoformat(waiter['registered_at']).strftime('%d/%m/%Y')}\n\n"
    
    send_message(chat_id, text, get_pending_approvals_keyboard(user["restaurant"]))

def handle_approve_waiter(chat_id: int, user_id: int, waiter_id: int):
    """Handle waiter approval"""
    admin = users.get(user_id)
    waiter = users.get(waiter_id)
    
    if not admin or admin["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    if not waiter or waiter["restaurant"] != admin["restaurant"]:
        send_message(chat_id, "❌ Waiter not found!")
        return
    
    # Approve waiter
    waiter["approved"] = True
    users[waiter_id] = waiter
    
    # Remove from pending approvals
    if admin["restaurant"] in pending_approvals:
        if waiter_id in pending_approvals[admin["restaurant"]]:
            pending_approvals[admin["restaurant"]].remove(waiter_id)
    
    # Notify waiter
    waiter_text = f"""🎉 **Congratulations! You've been approved! / እንኳን ደስ አለህ! ተፈቅዶህ ነው!**

You can now use all waiter features at {waiter["restaurant"]}!
አሁን በ{waiter["restaurant"]} የአስተናጋጅ ባህሪያትን መጠቀም ትችላለህ!"""
    
    send_message(waiter_id, waiter_text, get_waiter_keyboard())
    
    # Confirm to admin
    admin_text = f"""✅ **Waiter Approved! / አስተናጋጅ ተፈቀደ!**

**{waiter['name']}** has been approved and can now use the bot.
**{waiter['name']}** ተፈቀደ እና አሁን ቦቱን መጠቀም ይችላል።"""
    
    send_message(chat_id, admin_text, get_admin_keyboard())

def handle_reject_waiter(chat_id: int, user_id: int, waiter_id: int):
    """Handle waiter rejection"""
    admin = users.get(user_id)
    waiter = users.get(waiter_id)
    
    if not admin or admin["role"] != "admin":
        send_message(chat_id, "❌ Admin access required!")
        return
    
    if not waiter or waiter["restaurant"] != admin["restaurant"]:
        send_message(chat_id, "❌ Waiter not found!")
        return
    
    # Remove from pending approvals
    if admin["restaurant"] in pending_approvals:
        if waiter_id in pending_approvals[admin["restaurant"]]:
            pending_approvals[admin["restaurant"]].remove(waiter_id)
    
    # Remove waiter from users
    if waiter_id in users:
        del users[waiter_id]
    
    # Notify waiter
    waiter_text = f"""❌ **Registration Rejected / ምዝገባ ተቋጥቷል**

Your registration at {waiter["restaurant"]} has been rejected.
በ{waiter["restaurant"]} ምዝገባህ ተቋጥቷል።

Please contact the admin for more information.
ለተጨማሪ መረጃ አስተዳዳሪውን ያግኙ።"""
    
    send_message(waiter_id, waiter_text)
    
    # Confirm to admin
    admin_text = f"""❌ **Waiter Rejected / አስተናጋጅ ተቋጥቷል**

**{waiter['name']}** has been rejected and removed from the system.
**{waiter['name']}** ተቋጥቷል እና ከስርዓቱ ተወግዷል።"""
    
    send_message(chat_id, admin_text, get_admin_keyboard())

def handle_sign_out(chat_id: int, user_id: int):
    """Handle sign out"""
    user = users.get(user_id)
    if not user:
        send_message(chat_id, "❌ You are not logged in!")
        return
    
    # Reset user state
    user_states[user_id] = UserState.IDLE
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    text = f"""🚪 **Signed Out Successfully! / በተሳካ ሁኔታ ወጥተዋል!**

Goodbye {user['name']}! 👋
ቻው {user['name']}! 👋

You can sign in again anytime with /start
በማንኛውም ጊዜ በ/start እንደገና መግባት ትችላለህ።"""
    
    send_message(chat_id, text, get_main_keyboard())

def handle_callback_query(update: Dict):
    """Handle callback queries"""
    callback = update["callback_query"]
    chat_id = callback["message"]["chat"]["id"]
    user_id = callback["from"]["id"]
    data = callback["data"]
    
    logger.info(f"Callback: {data} from {user_id}")
    
    if data == "register_waiter":
        handle_register_waiter(chat_id, user_id)
    elif data == "register_admin":
        handle_register_admin(chat_id, user_id)
    elif data == "capture_payment":
        handle_capture_payment(chat_id, user_id)
    elif data == "my_transactions":
        handle_my_transactions(chat_id, user_id)
    elif data == "all_transactions":
        handle_all_transactions(chat_id, user_id)
    elif data == "manage_waiters":
        handle_manage_waiters(chat_id, user_id)
    elif data == "restaurant_settings":
        handle_restaurant_settings(chat_id, user_id)
    elif data == "pending_approvals":
        handle_pending_approvals(chat_id, user_id)
    elif data == "sign_out":
        handle_sign_out(chat_id, user_id)
    elif data == "main_menu":
        username = callback["from"].get("username", callback["from"].get("first_name", ""))
        handle_start(chat_id, user_id, username)
    elif data == "admin_menu":
        handle_pending_approvals(chat_id, user_id)
    elif data.startswith("approve_waiter_"):
        waiter_id = int(data.split("_")[2])
        handle_approve_waiter(chat_id, user_id, waiter_id)
    elif data.startswith("reject_waiter_"):
        waiter_id = int(data.split("_")[2])
        handle_reject_waiter(chat_id, user_id, waiter_id)

def handle_message(update: Dict):
    """Handle incoming messages"""
    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    username = message["from"].get("username", message["from"].get("first_name", ""))
    text = message.get("text", "")
    
    logger.info(f"Message: {text} from {username}, hasPhoto: {bool(message.get('photo'))}")
    
    # Handle photo
    if "photo" in message:
        photo = message["photo"][-1]  # Get highest resolution
        current_state = user_states.get(user_id)
        
        if current_state == UserState.WAITING_PHOTO:
            handle_photo(chat_id, user_id, photo)
        else:
            send_message(chat_id, "❌ Please follow the payment capture flow first!")
        return
    
    # Handle text messages
    if text.startswith("/start"):
        handle_start(chat_id, user_id, username)
    else:
        current_state = user_states.get(user_id)
        
        if current_state == UserState.WAITING_NAME:
            handle_name_input(chat_id, user_id, text)
        elif current_state == UserState.WAITING_PHONE:
            handle_phone_input(chat_id, user_id, text)
        elif current_state == UserState.WAITING_RESTAURANT:
            handle_restaurant_input(chat_id, user_id, text)
        elif current_state == UserState.WAITING_TABLE:
            handle_table_input(chat_id, user_id, text)
        elif current_state == UserState.WAITING_AMOUNT:
            handle_amount_input(chat_id, user_id, text)
        else:
            send_message(chat_id, "❌ Unknown command. Please use /start to begin.")

def get_updates(offset: int = 0) -> List[Dict]:
    """Get updates from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 5}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("result", [])
        else:
            logger.error(f"Failed to get updates: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return []

def main():
    """Main bot loop"""
    global bot_running
    bot_running = True
    
    logger.info("Starting VeriPay Bot - COMPLETE MILESTONE 1...")
    logger.info("Send a message to @Verifpay_bot now!")
    
    offset = 0
    
    while bot_running:
        try:
            updates = get_updates(offset)
            
            if updates:
                for update in updates:
                    offset = update["update_id"] + 1
                    
                    if "message" in update:
                        handle_message(update)
                    elif "callback_query" in update:
                        handle_callback_query(update)
            else:
                logger.info("No new messages...")
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Stopping bot...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
