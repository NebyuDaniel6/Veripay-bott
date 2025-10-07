#!/usr/bin/env python3
"""
Legacy UI module for VeriPay Bot
Provides restaurant/waiter registration menus and Amharic/English language support
"""

import os
from typing import Dict, List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

# Language Support
LANGUAGES = {
    "en": {
        "welcome": "🌟 **Welcome to VeriPay!** 🌟\n\nChoose your language / ቋንቋዎን ይምረጡ:",
        "main_menu": "🌟 **Welcome to VeriPay!** 🌟\n\nChoose your role to get started:",
        "register_restaurant": "🏢 Register Restaurant",
        "register_waiter": "👨‍💼 Register as Waiter",
        "help": "ℹ️ Help",
        "super_admin_menu": "🔴 **Super Admin Dashboard** 🔴\n\nManage the VeriPay system:",
        "restaurant_admin_menu": "🏪 **Restaurant Admin Dashboard** 🏪\n\nManage your restaurant:",
        "waiter_menu": "👨‍🍳 **Waiter Dashboard** 👨‍🍳\n\nCapture payments and manage orders:",
        "capture_payment": "💳 Capture Payment",
        "select_bank": "Please select the bank for the payment screenshot:",
        "upload_photo": "📸 Now upload a clear receipt photo.",
        "processing": "Processing screenshot, please wait...",
        "captured": "✅ Captured",
        "view_ocr": "🔎 View Full OCR Text",
        "pending_restaurants": "🏢 Pending Restaurant Approvals",
        "manage_waiters": "👥 Manage Waiters",
        "daily_reports": "📈 Daily Reports",
        "statistics": "📋 System Statistics",
        "settings": "⚙️ Settings",
        "back": "🔙 Back",
        "language": "🌐 Language",
        "restaurant_name_prompt": "🏢 **Restaurant Registration**\n\nPlease enter your restaurant name:",
        "restaurant_phone_prompt": "📱 Please enter your restaurant's phone number:",
        "waiter_name_prompt": "👨‍💼 **Waiter Registration**\n\nPlease enter your full name:",
        "waiter_phone_prompt": "📱 Please enter your phone number:",
        "registration_submitted": "✅ Registration submitted!\n\nYour registration is pending approval. You will be notified once approved.",
        "restaurant_approved": "🎉 Congratulations! Your restaurant has been approved!\n\nYou can now access the Restaurant Admin dashboard by typing /start",
        "restaurant_rejected": "❌ Sorry, your restaurant registration was not approved.\n\nPlease contact support for more information.",
        "waiter_approved": "🎉 Congratulations! You have been approved as a waiter!\n\nYou can now access the Waiter dashboard by typing /start",
        "waiter_rejected": "❌ Sorry, your waiter registration was not approved.\n\nPlease contact support for more information.",
    },
    "am": {
        "welcome": "🌟 **ወደ ቬሪፔይ እንኳን በደህና መጡ!** 🌟\n\nቋንቋዎን ይምረጡ / Choose your language:",
        "main_menu": "🌟 **ወደ ቬሪፔይ እንኳን በደህና መጡ!** 🌟\n\nለመጀመር ሚናዎን ይምረጡ:",
        "register_restaurant": "🏢 ሬስቶራንት ይመዝግቡ",
        "register_waiter": "👨‍💼 እንደ ወይተር ይመዝግቡ",
        "help": "ℹ️ እርዳታ",
        "super_admin_menu": "🔴 **ሱፐር አድሚን ዳሽቦርድ** 🔴\n\nየቬሪፔይ ሲስተምን ያስተዳድሩ:",
        "restaurant_admin_menu": "🏪 **የሬስቶራንት አድሚን ዳሽቦርድ** 🏪\n\nሬስቶራንትዎን ያስተዳድሩ:",
        "waiter_menu": "👨‍🍳 **የወይተር ዳሽቦርድ** 👨‍🍳\n\nክፍያዎችን ይያዙ እና ትዕዛዞችን ያስተዳድሩ:",
        "capture_payment": "💳 ክፍያ ይያዙ",
        "select_bank": "እባክዎ ለክፍያ ስክሪንሾት ባንኩን ይምረጡ:",
        "upload_photo": "📸 አሁን ግልፅ የሆነ ደረሰኝ ፎቶ ይስቀሉ።",
        "processing": "ስክሪንሾት በማቀነባበር ላይ፣ እባክዎ ይጠብቁ...",
        "captured": "✅ ተይዟል",
        "view_ocr": "🔎 ሙሉ OCR ጽሑፍ ይመልከቱ",
        "pending_restaurants": "🏢 በመጠባበቅ ላይ ያሉ የሬስቶራንት ማጽደቂያዎች",
        "manage_waiters": "👥 ወይተሮችን ያስተዳድሩ",
        "daily_reports": "📈 ዕለታዊ ሪፖርቶች",
        "statistics": "📋 የስርዓት ስታቲስቲክስ",
        "settings": "⚙️ ቅንብሮች",
        "back": "🔙 ተመለስ",
        "language": "🌐 ቋንቋ",
        "restaurant_name_prompt": "🏢 **የሬስቶራንት ምዝገባ**\n\nእባክዎ የሬስቶራንት ስም ያስገቡ:",
        "restaurant_phone_prompt": "📱 እባክዎ የሬስቶራንት ስልክ ቁጥር ያስገቡ:",
        "waiter_name_prompt": "👨‍💼 **የወይተር ምዝገባ**\n\nእባክዎ ሙሉ ስምዎን ያስገቡ:",
        "waiter_phone_prompt": "📱 እባክዎ የስልክ ቁጥርዎን ያስገቡ:",
        "registration_submitted": "✅ ምዝገባ ተልኳል!\n\nየእርስዎ ምዝገባ በመጠባበቅ ላይ ነው። ከተፀድቀ በኋላ ይሳተፋሉ።",
        "restaurant_approved": "🎉 እንኳን ደስ አለዎት! የእርስዎ ሬስቶራንት ተፀድቋል!\n\nአሁን የሬስቶራንት አድሚን ዳሽቦርድ በ /start በመጻፍ መድረስ ይችላሉ",
        "restaurant_rejected": "❌ ይቅርታ፣ የእርስዎ የሬስቶራንት ምዝገባ አልተፀድቀም።\n\nለተጨማሪ መረጃ እባክዎ ድጋፍን ያግኙ።",
        "waiter_approved": "🎉 እንኳን ደስ አለዎት! እንደ ወይተር ተፀድቀዋል!\n\nአሁን የወይተር ዳሽቦርድ በ /start በመጻፍ መድረስ ይችላሉ",
        "waiter_rejected": "❌ ይቅርታ፣ የእርስዎ የወይተር ምዝገባ አልተፀድቀም።\n\nለተጨማሪ መረጃ እባክዎ ድጋፍን ያግኙ።",
    }
}

# User roles
from enum import Enum
class UserRole(Enum):
    NEW_USER = "new_user"
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

# User states
class UserState:
    IDLE = "idle"
    SELECTING_LANGUAGE = "selecting_language"
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_RESTAURANT_SELECTION = "waiting_for_restaurant_selection"
    CAPTURING_PAYMENT = "capturing_payment"
    WAITING_FOR_RECEIPT_IMAGE = "waiting_for_receipt_image"
    SELECTING_BANK = "selecting_bank"

# Bank buttons
BANK_BUTTONS = [
    ("🏦 CBE", "bank_cbe"),
    ("📱 Telebirr", "bank_telebirr"),
    ("🏦 Dashen", "bank_dashen"),
    ("🏦 Abyssinia", "bank_abyssinia"),
]

def get_text(user_id: int, key: str, user_languages: Dict[int, str]) -> str:
    """Get localized text for user"""
    lang = user_languages.get(user_id, "en")
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, key)

def build_language_selection_keyboard() -> InlineKeyboardMarkup:
    """Build language selection keyboard"""
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇪🇹 አማርኛ (Amharic)", callback_data="lang_am")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_main_menu_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build main registration menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔑 Login", callback_data="login")],
        [InlineKeyboardButton(get_text(user_id, "register_restaurant", user_languages), callback_data="register_restaurant")],
        [InlineKeyboardButton(get_text(user_id, "register_waiter", user_languages), callback_data="register_waiter")],
        [InlineKeyboardButton(get_text(user_id, "help", user_languages), callback_data="help")],
        [InlineKeyboardButton(get_text(user_id, "language", user_languages), callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_super_admin_menu_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build Super Admin menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "pending_restaurants", user_languages), callback_data="super_pending_restaurants")],
        [InlineKeyboardButton("📊 Active Restaurants", callback_data="super_active_restaurants")],
        [InlineKeyboardButton(get_text(user_id, "daily_reports", user_languages), callback_data="super_daily_reports")],
        [InlineKeyboardButton(get_text(user_id, "statistics", user_languages), callback_data="super_statistics")],
        [InlineKeyboardButton(get_text(user_id, "settings", user_languages), callback_data="super_settings")],
        [InlineKeyboardButton("🔓 Logout", callback_data="logout")],
        [InlineKeyboardButton("🔓 Logout", callback_data="logout")],
        [InlineKeyboardButton(get_text(user_id, "language", user_languages), callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_restaurant_admin_menu_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build Restaurant Admin menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "manage_waiters", user_languages), callback_data="restaurant_manage_waiters")],
        [InlineKeyboardButton("📒 Restaurant Transactions", callback_data="restaurant_transactions")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="restaurant_settings")],
        [InlineKeyboardButton("📄 Upload Statement", callback_data="restaurant_recon_upload")],
        [InlineKeyboardButton("🧮 Run Reconciliation", callback_data="restaurant_recon_run")],
        [InlineKeyboardButton("📥 Download Last Report", callback_data="restaurant_recon_download")],
        [InlineKeyboardButton("🔓 Logout", callback_data="logout")],
        [InlineKeyboardButton(get_text(user_id, "language", user_languages), callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_waiter_menu_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build Waiter menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "capture_payment", user_languages), callback_data="waiter_capture_payment")],
        [InlineKeyboardButton("📒 My Transactions", callback_data="waiter_transactions")],
        [InlineKeyboardButton(get_text(user_id, "help", user_languages), callback_data="waiter_help")],
        [InlineKeyboardButton("🔓 Logout", callback_data="logout")],
        [InlineKeyboardButton(get_text(user_id, "language", user_languages), callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_bank_selection_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build bank selection keyboard"""
    keyboard = []
    for text, callback_data in BANK_BUTTONS:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    keyboard.append([InlineKeyboardButton("Other", callback_data="bank_other")])
    keyboard.append([InlineKeyboardButton(get_text(user_id, "back", user_languages), callback_data="back_to_waiter")])
    return InlineKeyboardMarkup(keyboard)

def build_payment_result_keyboard(user_id: int, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build payment result keyboard"""
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "view_ocr", user_languages), callback_data="view_ocr_text")],
        [InlineKeyboardButton(get_text(user_id, "back", user_languages), callback_data="back_to_waiter")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_pending_restaurants_keyboard(user_id: int, pending_restaurants: Dict, user_languages: Dict[int, str]) -> InlineKeyboardMarkup:
    """Build pending restaurants approval keyboard"""
    keyboard = []
    for reg_user_id, data in pending_restaurants.items():
        keyboard.append([
            InlineKeyboardButton(f"✅ Approve {data['name']}", callback_data=f"approve_restaurant_{reg_user_id}"),
            InlineKeyboardButton(f"❌ Reject", callback_data=f"reject_restaurant_{reg_user_id}")
        ])
    keyboard.append([InlineKeyboardButton(get_text(user_id, "back", user_languages), callback_data="back_to_super_admin")])
    return InlineKeyboardMarkup(keyboard)

def build_back_keyboard(user_id: int, user_languages: Dict[int, str], back_callback: str = "back_to_main") -> InlineKeyboardMarkup:
    """Build simple back keyboard"""
    keyboard = [[InlineKeyboardButton(get_text(user_id, "back", user_languages), callback_data=back_callback)]]
    return InlineKeyboardMarkup(keyboard)
