import logging
import os
from io import BytesIO
from typing import Tuple, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from state import StateStore
from storage import Storage
from ocr import VisionOCR
import re
import asyncio
from telegram.error import BadRequest, TimedOut, NetworkError, RetryAfter
from flask import Flask, jsonify
from pdf_generator import PDFGenerator
from datetime import datetime

# Import legacy UI if enabled
from m2_handler import handle_upload_statement, handle_document_upload, handle_reconciliation
LEGACY_UI = os.environ.get("LEGACY_UI", "0") == "1"
if LEGACY_UI:
    from ui_legacy import (
        LANGUAGES, UserRole, UserState, BANK_BUTTONS,
        get_text, build_language_selection_keyboard, build_main_menu_keyboard,
        build_super_admin_menu_keyboard, build_restaurant_admin_menu_keyboard,
        build_waiter_menu_keyboard, build_bank_selection_keyboard,
        build_payment_result_keyboard, build_pending_restaurants_keyboard,
        build_back_keyboard
    )


# Error handling and safe messaging
async def safe_send(update, text: str, **kwargs):
    """Send message safely with fallback for BadRequest errors"""
    try:
        if update.message:
            return await update.message.reply_text(text, **kwargs)
        else:
            return await update.effective_chat.send_message(text, **kwargs)
    except BadRequest as e:
        # Fallback: remove parse_mode and truncate if too long
        fallback_kwargs = {k: v for k, v in kwargs.items() if k != 'parse_mode'}
        fallback_text = text[:4000] + '...' if len(text) > 4000 else text
        # Remove problematic characters that cause Markdown issues
        fallback_text = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', '', fallback_text)
        try:
            if update.message:
                return await update.message.reply_text(fallback_text, **fallback_kwargs)
            else:
                return await update.effective_chat.send_message(fallback_text, **fallback_kwargs)
        except Exception as fallback_error:
            print(f'FATAL: Could not send message even with fallback: {fallback_error}')
            return None
    except Exception as e:
        print(f'ERROR in safe_send: {e}')
        return None

async def safe_edit(update, text: str, **kwargs):
    """Edit message safely with fallback for BadRequest errors"""
    try:
        return await update.callback_query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        # Fallback: remove parse_mode and truncate if too long
        fallback_kwargs = {k: v for k, v in kwargs.items() if k != 'parse_mode'}
        fallback_text = text[:4000] + '...' if len(text) > 4000 else text
        # Remove problematic characters that cause Markdown issues
        fallback_text = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', '', fallback_text)
        try:
            return await update.callback_query.edit_message_text(fallback_text, **fallback_kwargs)
        except Exception as fallback_error:
            print(f'FATAL: Could not edit message even with fallback: {fallback_error}')
            return None
    except Exception as e:
        print(f'ERROR in safe_edit: {e}')
        return None

# Global error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler that prevents the bot from stopping"""
    logger = logging.getLogger(__name__)
    err = context.error
    logger.error(f'Exception while handling an update: {err}', exc_info=err)
    
    # Ignore transient network/timeouts silently
    if isinstance(err, (TimedOut, RetryAfter, NetworkError)):
        return

    # For non-transient errors, gently inform the user
    if update and hasattr(update, 'effective_user'):
        try:
            await safe_send(update, 'Sorry, something went wrong. Please try again.')
        except:
            pass  # Do not crash even if notifying fails

# Health check endpoint for monitoring  
app_flask = Flask(__name__)

@app_flask.route('/health', methods=['GET'])

# Health check command handler
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check command"""
    await safe_send(update, '🟢 Bot is healthy and running!')

def health_check():
    try:
        loop = asyncio.get_event_loop()
        timestamp = int(loop.time()) if loop.is_running() else 0
    except:
        timestamp = 0
    
    return jsonify({
        'status': 'healthy',
        'bot': 'running', 
        'timestamp': timestamp
    })

def ensure_user_in_memory(user_id: int, storage: Storage) -> None:
    """Ensure user is loaded from database into memory"""
    if user_id not in users:
        db_user = storage.get_user_by_telegram(user_id)
        if db_user:
            users[user_id] = {
                'id': user_id,
                'username': db_user.get('username', 'Unknown'),
                'role': UserRole(db_user.get('role', 'NEW_USER')),
                'restaurant_id': None,
                'waiter_id': None,
                'created_at': None
            }
            user_languages[user_id] = db_user.get('language', 'en')
            user_states[user_id] = UserState.IDLE
        else:
            # User not found in database, create new user
            users[user_id] = {
                'id': user_id,
                'username': 'Unknown',
                'role': UserRole.NEW_USER,
                'restaurant_id': None,
                'waiter_id': None,
                'created_at': None
            }
            user_languages[user_id] = 'en'
            user_states[user_id] = UserState.SELECTING_LANGUAGE



logger = logging.getLogger(__name__)

# Simple UI bank buttons (fallback)
SIMPLE_BANK_BUTTONS = [
    ("🏦 CBE", "bank_cbe"),
    ("📱 Telebirr", "bank_telebirr"),
    ("🏦 Dashen", "bank_dashen"),
    ("🏦 Abyssinia", "bank_abyssinia"),
]

state = StateStore()
storage: Storage
ocr: VisionOCR

# Legacy UI state management
if LEGACY_UI:
    users: Dict[int, Dict] = {}
    user_states: Dict[int, str] = {}
    user_languages: Dict[int, str] = {}
    pending_restaurant_approvals: Dict[int, Dict] = {}
    pending_waiter_approvals: Dict[int, Dict] = {}
    user_ocr_texts: Dict[int, str] = {}
    user_selected_banks: Dict[int, str] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler
    PRD:M1.0 Entry & Role Routing; Rules: dev polling, single instance
    """
    user = update.effective_user
    user_id = user.id
    super_admin_id = int(os.environ.get("SUPER_ADMIN_ID", "0") or 0)
    
    if not LEGACY_UI:
        # Simple UI mode
        state.set_role(user_id, "waiter" if str(user_id) != os.environ.get("SUPER_ADMIN_ID", "") else "super_admin")
        buttons = [[InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")]]
        try:
            if update.message:
                await update.message.reply_text("Welcome to VeriPay. Use menu buttons.", reply_markup=InlineKeyboardMarkup(buttons))
            else:
                await update.effective_chat.send_message("Welcome to VeriPay. Use menu buttons.", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            # Fallback to chat send if any reply error
            await update.effective_chat.send_message("Welcome to VeriPay. Use menu buttons.", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Legacy UI mode
    username = user.username or "Unknown"

    # Check database first for existing user
    db_user = storage.get_user_by_telegram(user_id)
    
    # Immediate super admin recognition (auto-login)
    if user_id == super_admin_id:
        # Ensure super admin is in database
        if not db_user:
            storage.upsert_user(user_id, username, None, role='SUPER_ADMIN', language='en')
        else:
            storage.set_user_role(user_id, 'SUPER_ADMIN')
        
        # Set up in-memory state
        users[user_id] = {
            'id': user_id,
            'username': username,
            'role': UserRole.SUPER_ADMIN,
            'restaurant_id': None,
            'waiter_id': None,
            'created_at': None
        }
        if user_id not in user_languages:
            user_languages[user_id] = db_user.get('language', 'en') if db_user else 'en'
        user_states[user_id] = UserState.IDLE
        await setup_persistent_keyboard(update, user_id, 'SUPER_ADMIN')
        return
    
    # Check if user exists in database
    if db_user:
        # User exists - restore their role and state
        role = db_user.get('role', 'NEW_USER')
        try:
            user_role = getattr(UserRole, role, UserRole.NEW_USER)
        except KeyError:
            user_role = UserRole.NEW_USER
        
        users[user_id] = {
            'id': user_id,
            'username': username,
            'role': user_role,
            'restaurant_id': None,
            'waiter_id': None,
            'created_at': None
        }
        user_languages[user_id] = db_user.get('language', 'en')
        
        # Route to appropriate dashboard based on role
        if role == 'SUPER_ADMIN':
            user_states[user_id] = UserState.IDLE
            await setup_persistent_keyboard(update, user_id, 'SUPER_ADMIN')
        elif role == 'RESTAURANT_ADMIN':
            user_states[user_id] = UserState.IDLE
            await setup_persistent_keyboard(update, user_id, 'RESTAURANT_ADMIN')
        elif role == 'WAITER':
            user_states[user_id] = UserState.IDLE
            await setup_persistent_keyboard(update, user_id, 'WAITER')
        else:
            user_states[user_id] = UserState.SELECTING_LANGUAGE
            await show_language_selection(update)
        return
    
    # New user - initialize in database and memory
    storage.upsert_user(user_id, username, None, role='NEW_USER', language='en')
    users[user_id] = {
        'id': user_id,
        'username': username,
        'role': UserRole.NEW_USER,
        'restaurant_id': None,
        'waiter_id': None,
        'created_at': None
    }
    user_states[user_id] = UserState.SELECTING_LANGUAGE
    user_languages[user_id] = 'en'
    
    # Show language selection for new users
    await show_language_selection(update)
    return
    
    # Check if user is Super Admin
    if user_id == int(os.environ.get("SUPER_ADMIN_ID", "0")):
        users[user_id]['role'] = UserRole.SUPER_ADMIN
    
    # Show appropriate menu based on role
    if users[user_id]['role'] == UserRole.SUPER_ADMIN:
        await show_super_admin_menu(update)
    elif users[user_id]['role'] == UserRole.RESTAURANT_ADMIN:
        await show_restaurant_admin_menu(update)
    elif users[user_id]['role'] == UserRole.WAITER:
        await show_waiter_menu(update)
    else:
        await show_main_menu(update)

async def show_language_selection(update: Update):
    """Show language selection menu"""
    keyboard = build_language_selection_keyboard()
    text = LANGUAGES["en"]["welcome"]
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_main_menu(update: Update):
    """Show main registration menu"""
    user_id = update.effective_user.id
    keyboard = build_main_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "main_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_super_admin_menu(update: Update):
    """Show Super Admin menu"""
    user_id = update.effective_user.id
    keyboard = build_super_admin_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "super_admin_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    # send persistent reply keyboard
    try:
        reply_kb = ReplyKeyboardMarkup([[KeyboardButton("🏠 Home"), KeyboardButton("🧭 Menu"), KeyboardButton("❓ Help")]], resize_keyboard=True, one_time_keyboard=False)
        await update.effective_chat.send_message(" ", reply_markup=reply_kb)
    except Exception:
        pass

async def show_restaurant_admin_menu(update: Update):
    """Show Restaurant Admin menu"""
    user_id = update.effective_user.id
    keyboard = build_restaurant_admin_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "restaurant_admin_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    # send persistent reply keyboard
    try:
        reply_kb = ReplyKeyboardMarkup([[KeyboardButton("🏠 Home"), KeyboardButton("🧭 Menu"), KeyboardButton("❓ Help")]], resize_keyboard=True, one_time_keyboard=False)
        await update.effective_chat.send_message(" ", reply_markup=reply_kb)
    except Exception:
        pass

async def show_waiter_menu(update: Update):
    """Show Waiter menu"""
    user_id = update.effective_user.id
    keyboard = build_waiter_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "waiter_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    # send persistent reply keyboard
    try:
        reply_kb = ReplyKeyboardMarkup([[KeyboardButton("🏠 Home"), KeyboardButton("🧭 Menu"), KeyboardButton("❓ Help")]], resize_keyboard=True, one_time_keyboard=False)
        await update.effective_chat.send_message(" ", reply_markup=reply_kb)
    except Exception:
        pass

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback dispatcher
    PRD:M1.* UI Navigation & Actions
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    # Debug logging
    print(f"DEBUG: Main callback handler received '{data}' from user {user_id}")
    logger.info(f"DEBUG: Main callback handler received '{data}' from user {user_id}")
    
    await query.answer()
    
    if not LEGACY_UI:
        # Simple UI mode - existing logic
        if data == "capture_payment":
            kb = [[InlineKeyboardButton(txt, callback_data=cb)] for (txt, cb) in SIMPLE_BANK_BUTTONS]
            kb.append([InlineKeyboardButton("Other", callback_data="bank_other")])
            state.set_step(user_id, "waiting_bank")
            await query.edit_message_text("Select bank:", reply_markup=InlineKeyboardMarkup(kb))
            return
        
        if data.startswith("bank_"):
            mapping = {
                "bank_cbe": "Commercial Bank of Ethiopia",
                "bank_telebirr": "Telebirr",
                "bank_dashen": "Dashen Bank",
                "bank_abyssinia": "Bank of Abyssinia",
                "bank_other": "Unknown",
            }
            chosen = mapping.get(data, "Unknown")
            state.set_bank(user_id, chosen)
            state.set_step(user_id, "waiting_receipt")
            await query.edit_message_text(f"✅ Bank selected: {chosen}\n\n📸 Now upload a clear receipt photo.")
            return
        
        if data == "view_full_ocr":
            full_text = state.get_last_ocr_text(user_id) or "(no OCR text)"
            await query.edit_message_text(full_text[:3900])
            return
        
        return
    
    # Legacy UI mode - handle all callbacks
    await handle_legacy_callback(update, context)

async def handle_legacy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all legacy UI callbacks
    PRD:M1.1 Registration; M1.2 Waiter Capture; M1.4 Super Admin
    """
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    # Debug logging
    print(f"DEBUG: Received callback '{data}' from user {user_id}")
    logger.info(f"DEBUG: Received callback '{data}' from user {user_id}")
    # Language selection
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_languages[user_id] = lang
        user_states[user_id] = UserState.IDLE
        super_admin_id = int(os.environ.get("SUPER_ADMIN_ID", "0") or 0)
        if user_id == super_admin_id:
            users[user_id] = users.get(user_id, {
                'id': user_id,
                'username': (update.effective_user.username or "Unknown"),
                'role': UserRole.SUPER_ADMIN,
                'restaurant_id': None,
                'waiter_id': None,
                'created_at': None
            })
            users[user_id]['role'] = UserRole.SUPER_ADMIN
            await show_super_admin_menu(update)
        else:
            await show_main_menu(update)
        return
    
    # Change language
    if data == "change_language":
        await show_language_selection(update)
        return
    
    # Restaurant registration
    if data == "register_restaurant":
        await start_restaurant_registration(update)
        return
    
    # Waiter registration
    if data == "register_waiter":
        await start_waiter_registration(update)
        return
    
    # Waiter capture payment
    if data == "waiter_capture_payment":
        await start_payment_capture(update)
        return
    
    # Bank selection
    if data.startswith("bank_"):
        await handle_bank_selection(update, data)
        return
    
    # View OCR text
    if data == "view_ocr_text":
        await show_ocr_text(update)
        return
    
    # Restaurant approval actions (handle directly)
    if data.startswith("approve_restaurant_"):
        restaurant_user_id = int(data.split("_")[-1])
        print(f"DEBUG: Direct approval processing for user {restaurant_user_id}")
        logger.info(f"DEBUG: Direct approval processing for user {restaurant_user_id}")
        await approve_restaurant(update, restaurant_user_id)
        return
    
    if data.startswith("reject_restaurant_"):
        restaurant_user_id = int(data.split("_")[-1])
        await reject_restaurant(update, restaurant_user_id)
        return
    
    # Waiter approval actions (handle directly)
    if data.startswith("restaurant_approve_waiter_"):
        waiter_user_id = int(data.split("_")[-1])
        print(f"DEBUG: Direct waiter approval processing for user {waiter_user_id}")
        logger.info(f"DEBUG: Direct waiter approval processing for user {waiter_user_id}")
        await approve_waiter(update, waiter_user_id)
        return
    
    if data.startswith("restaurant_reject_waiter_"):
        waiter_user_id = int(data.split("_")[-1])
        await reject_waiter(update, waiter_user_id)
        return
    


    # Waiter actions
    if data.startswith("waiter_"):
        await handle_waiter_action(update, data)
        return
    
    # Restaurant Admin actions
    if data.startswith("restaurant_"):
        await handle_restaurant_admin_action(update, data)
        return
    
    # Super Admin actions
    if data.startswith("super_"):
        await handle_super_admin_action(update, data)
        return
    
    # Restaurant Admin actions
    if data.startswith("restaurant_"):
        await handle_restaurant_admin_action(update, data)
        return
    
    # Back buttons
    if data == "back_to_main":
        await show_main_menu(update)
        return
    elif data == "back_to_super_admin":
        await show_super_admin_menu(update)
        return
    elif data == "back_to_restaurant_admin":
        await show_restaurant_admin_menu(update)
        return
    elif data == "back_to_waiter":
        await show_waiter_menu(update)
        return
    
    # Default: show appropriate menu
    if users[user_id]['role'] == UserRole.SUPER_ADMIN:
        await show_super_admin_menu(update)
    elif users[user_id]['role'] == UserRole.RESTAURANT_ADMIN:
        await show_restaurant_admin_menu(update)
    elif users[user_id]['role'] == UserRole.WAITER:
        await show_waiter_menu(update)
    else:
        await show_main_menu(update)




async def setup_persistent_keyboard_for_user(bot, user_id: int, role: str):
    """Set up persistent inline keyboard for a specific user"""
    if role == 'SUPER_ADMIN':
        keyboard = build_super_admin_menu_keyboard(user_id, user_languages)
        text = "🔧 **Super Admin Dashboard**\n\nWelcome! Use the menu below to manage the system."
    elif role == 'RESTAURANT_ADMIN':
        keyboard = build_restaurant_admin_menu_keyboard(user_id, user_languages)
        text = "🏪 **Restaurant Admin Dashboard**\n\nWelcome! Use the menu below to manage your restaurant."
    elif role == 'WAITER':
        keyboard = build_waiter_menu_keyboard(user_id, user_languages)
        text = "👨‍💼 **Waiter Dashboard**\n\nWelcome! Use the menu below to capture payments and view transactions."
    else:
        keyboard = build_main_menu_keyboard(user_id, user_languages)
        text = "🏠 **VeriPay**\n\nWelcome! Please select your role to get started."
    
    await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard, parse_mode='Markdown')


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu command to show persistent keyboard"""
    user_id = update.effective_user.id
    
    if not LEGACY_UI:
        await update.message.reply_text("Use the inline buttons above.")
        return
    
    # Ensure user is in memory
    ensure_user_in_memory(user_id, storage)
    
    # Get user role
    role = users[user_id]['role'].value if user_id in users else 'NEW_USER'
    
    # Show appropriate persistent keyboard
    await setup_persistent_keyboard(update, user_id, role)


async def setup_persistent_keyboard(update: Update, user_id: int, role: str):
    """Set up persistent inline keyboard for the user's role"""
    if role == 'SUPER_ADMIN':
        keyboard = build_super_admin_menu_keyboard(user_id, user_languages)
        text = "🔧 **Super Admin Dashboard**\n\nWelcome! Use the menu below to manage the system."
    elif role == 'RESTAURANT_ADMIN':
        keyboard = build_restaurant_admin_menu_keyboard(user_id, user_languages)
        text = "🏪 **Restaurant Admin Dashboard**\n\nWelcome! Use the menu below to manage your restaurant."
    elif role == 'WAITER':
        keyboard = build_waiter_menu_keyboard(user_id, user_languages)
        text = "👨‍💼 **Waiter Dashboard**\n\nWelcome! Use the menu below to capture payments and view transactions."
    else:
        keyboard = build_main_menu_keyboard(user_id, user_languages)
        text = "🏠 **VeriPay**\n\nWelcome! Please select your role to get started."
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                await update.callback_query.answer("Already up to date!")
            else:
                raise
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route user to their role dashboard (Home/Menu)."""
    if not LEGACY_UI:
        return
    user_id = update.effective_user.id
    # Ensure user present and determine role string
    ensure_user_in_memory(user_id, storage)
    role_value = users.get(user_id, {}).get('role', UserRole.NEW_USER)
    role_str = getattr(role_value, 'value', role_value) if role_value else 'NEW_USER'
    await setup_persistent_keyboard(update, user_id, role_str)

async def start_payment_capture(update: Update):
    """Start payment capture flow"""
    user_id = update.callback_query.from_user.id
    user_states[user_id] = UserState.SELECTING_BANK
    
    keyboard = build_bank_selection_keyboard(user_id, user_languages)
    text = get_text(user_id, "select_bank", user_languages)
    
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def handle_bank_selection(update: Update, bank_data: str):
    """Handle bank selection"""
    user_id = update.callback_query.from_user.id
    
    bank_mapping = {
        "bank_cbe": "Commercial Bank of Ethiopia",
        "bank_telebirr": "Telebirr",
        "bank_dashen": "Dashen Bank",
        "bank_abyssinia": "Bank of Abyssinia",
        "bank_other": "Other"
    }
    
    selected_bank = bank_mapping.get(bank_data, "Unknown")
    user_selected_banks[user_id] = selected_bank
    user_states[user_id] = UserState.WAITING_FOR_RECEIPT_IMAGE
    
    text = f"✅ Bank selected: {selected_bank}\n\n{get_text(user_id, 'upload_photo', user_languages)}"
    await update.callback_query.edit_message_text(text)

async def start_restaurant_registration(update: Update):
    """Start restaurant registration process"""
    user_id = update.callback_query.from_user.id
    user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
    
    text = get_text(user_id, "restaurant_name_prompt", user_languages)
    await update.callback_query.edit_message_text(text, parse_mode='Markdown')

async def start_waiter_registration(update: Update):
    """Start waiter registration process"""
    user_id = update.callback_query.from_user.id
    user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
    
    text = get_text(user_id, "waiter_name_prompt", user_languages)
    await update.callback_query.edit_message_text(text, parse_mode='Markdown')

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on user state"""
    if not LEGACY_UI:
        return  # Simple UI doesn't handle text messages
    
    user_id = update.effective_user.id
    text = update.message.text
    
    # Minimal persistent navigation mapping
    if text in ["🏠 Home", "🧭 Menu", "/menu", "/start"]:
        await show_home(update, context)
        return
    if text == "❓ Help":
        # Prefer waiter help if role is waiter; otherwise route to home
        role_val = users.get(user_id, {}).get('role')
        if role_val == UserRole.WAITER:
            # Fall back to a simple help message in text context
            await update.message.reply_text(
                "❓ Waiter Help\n\nUse ‘📸 Capture Payment’, then upload a clear receipt.",
                parse_mode='Markdown'
            )
        else:
            await show_home(update, context)
        return
    
    state_name = user_states.get(user_id, UserState.IDLE)
    
    if state_name == UserState.WAITING_FOR_RESTAURANT_NAME:
        # Store restaurant name and ask for phone
        if 'temp_registrations' not in globals():
            globals()['temp_registrations'] = {}
        temp_registrations[user_id] = {'name': text}
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(get_text(user_id, "restaurant_phone_prompt", user_languages))
    
    elif state_name == UserState.WAITING_FOR_RESTAURANT_PHONE:
        # Complete restaurant registration
        if 'temp_registrations' in globals() and user_id in temp_registrations:
            restaurant_data = temp_registrations[user_id]
            restaurant_data['phone'] = text
            restaurant_data['user_id'] = user_id
            
            # Add to pending approvals
            pending_restaurant_approvals[user_id] = restaurant_data
            
            # Notify Super Admin
            await notify_super_admin_restaurant_registration(user_id, restaurant_data)
            
            await update.message.reply_text(get_text(user_id, "registration_submitted", user_languages))
            
            # Clean up
            del temp_registrations[user_id]
            user_states[user_id] = UserState.IDLE
    
    elif state_name == UserState.WAITING_FOR_WAITER_NAME:
        # Store waiter name and ask for phone
        if 'temp_registrations' not in globals():
            globals()['temp_registrations'] = {}
        temp_registrations[user_id] = {'name': text}
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text(get_text(user_id, "waiter_phone_prompt", user_languages))
    
    elif state_name == UserState.WAITING_FOR_WAITER_PHONE:
        # Complete waiter registration
        if 'temp_registrations' in globals() and user_id in temp_registrations:
            waiter_data = temp_registrations[user_id]
            waiter_data['phone'] = text
            waiter_data['user_id'] = user_id
            
            # Add to pending approvals
            pending_waiter_approvals[user_id] = waiter_data
            
            await update.message.reply_text(get_text(user_id, "registration_submitted", user_languages))
            
            # Clean up
            del temp_registrations[user_id]
            user_states[user_id] = UserState.IDLE

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not LEGACY_UI:
        # Simple UI mode
        if state.get_step(user_id) != "waiting_receipt":
            await update.message.reply_text("Please use the menu to start: tap 📸 Capture Payment.")
            return
    else:
        # Legacy UI mode
        if user_states.get(user_id) != UserState.WAITING_FOR_RECEIPT_IMAGE:
            await update.message.reply_text("Please start payment capture first using the menu.")
            return
    
    await update.message.reply_text(get_text(user_id, "processing", user_languages) if LEGACY_UI else "Processing screenshot, please wait...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download image
        bio = BytesIO()
        await file.download_to_memory(out=bio)
        image_bytes = bio.getvalue()
        
        # Get selected bank
        if LEGACY_UI:
            bank_hint = user_selected_banks.get(user_id, "Unknown")
        else:
            bank_hint = state.get_bank(user_id)
        
        # Process with OCR
        ocr_result = ocr.extract(image_bytes, bank_hint=bank_hint)
        
        if ocr_result:
            # Store OCR text for viewing
            full_text = ocr_result.get("raw_text", "")
            if LEGACY_UI:
                user_ocr_texts[user_id] = full_text
            else:
                state.set_last_ocr_text(user_id, full_text)
            
            # Extract OCR data first
            bank = ocr_result.get("bank", "Unknown")
            amount = ocr_result.get("amount", "Unknown")
            sender = ocr_result.get("sender", "Unknown")
            time_val = ocr_result.get("time", "Unknown")
            ref = ocr_result.get("reference", "")
            
            # Store transaction in database
            try:
                # Get waiter and restaurant info
                waiter = storage.get_waiter_by_user_telegram(user_id)
                restaurant_id = waiter.get('restaurant_id') if waiter else None
                waiter_id = waiter.get('id') if waiter else None
                
                print(f"DEBUG: Waiter info - ID: {waiter_id}, Restaurant ID: {restaurant_id}")
                
                # Store media file info
                media_id = storage.insert_media(
                    telegram_file_id=photo.file_id,
                    file_path=file.file_path,
                    file_size=photo.file_size,
                    mime_type="image/jpeg"
                )
                
                print(f"DEBUG: Media stored with ID: {media_id}")
                
                # Store transaction
                transaction_id = storage.insert_transaction(
                    restaurant_id=restaurant_id,
                    waiter_id=waiter_id,
                    media_id=media_id,
                    bank=bank,
                    amount=amount if amount != "Unknown" else None,
                    currency='ETB',
                    transaction_id=ref,
                    transaction_date=None,
                    transaction_time=None,
                    payer=sender,
                    receiver=None,
                    original_ref=ref,
                    status='completed',
                    raw_ocr_text=full_text
                )
                
                print(f"DEBUG: Stored transaction {transaction_id} for waiter {waiter_id}, restaurant {restaurant_id}")
                logger.info(f"Stored transaction {transaction_id} for waiter {waiter_id}, restaurant {restaurant_id}")
                
            except Exception as e:
                print(f"DEBUG: Error storing transaction: {e}")
                logger.error(f"Error storing transaction: {e}")
            
            # Format result
            
            result_parts = [
                get_text(user_id, "captured", user_languages) if LEGACY_UI else "✅ Captured",
                f"- Bank: {bank}",
                f"- Amount: {amount} ETB" if amount != "Unknown" else "- Amount: Unknown",
                f"- Sender: {sender}",
                f"- Time: {time_val}",
            ]
            
            if ref:
                result_parts.append(f"- Ref: {ref}")
            
            if LEGACY_UI:
                keyboard = build_payment_result_keyboard(user_id, user_languages)
            else:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔎 View Full OCR", callback_data="view_full_ocr")]])
            
            await update.message.reply_text(
                "\n".join(result_parts),
                reply_markup=keyboard
            )
            
            # Reset state
            if LEGACY_UI:
                user_states[user_id] = UserState.IDLE
            else:
                state.set_step(user_id, None)
        
        else:
            await update.message.reply_text("❌ Could not process the image. Please try again with a clearer photo.")
    
    except Exception as e:
        logger.error(f"Error processing image for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error processing image: {e}")

async def show_ocr_text(update: Update):
    """Show full OCR text"""
    user_id = update.callback_query.from_user.id
    
    if LEGACY_UI and user_id in user_ocr_texts:
        ocr_text = user_ocr_texts[user_id]
    elif not LEGACY_UI:
        ocr_text = state.get_last_ocr_text(user_id) or "(no OCR text)"
    else:
        ocr_text = "(no OCR text)"
    
    # Limit text length for Telegram
    if len(ocr_text) > 3900:
        ocr_text = ocr_text[:3900] + "..."
    
    text = f"**Full OCR Text:**\n```\n{ocr_text}\n```"
    
    if LEGACY_UI:
        keyboard = build_back_keyboard(user_id, user_languages, "back_to_waiter")
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
    
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def notify_super_admin_restaurant_registration(user_id: int, restaurant_data: Dict):
    """Notify Super Admin of new restaurant registration"""
    try:
        super_admin_id = int(os.environ.get("SUPER_ADMIN_ID", "0"))
        if not super_admin_id:
            return
        
        text = (
            f"🏢 **New Restaurant Registration**\n\n"
            f"Restaurant: {restaurant_data['name']}\n"
            f"Phone: {restaurant_data['phone']}\n"
            f"User ID: {user_id}\n\n"
            f"Please review and approve/reject."
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_restaurant_{user_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_restaurant_{user_id}")]
        ])
        
        from telegram import Bot
        bot = Bot(token=os.environ.get("BOT_TOKEN"))
        await bot.send_message(
            chat_id=super_admin_id,
            text=text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    except Exception as e:
        logger.error(f"Error notifying Super Admin: {e}")

async def handle_super_admin_action(update: Update, action: str):
    """Handle Super Admin actions
    PRD:M1.4 Restaurant approval by Super Admin; Rules: role separation
    """
    user_id = update.callback_query.from_user.id
    super_admin_id = int(os.environ.get("SUPER_ADMIN_ID", "0"))
    
    if user_id != super_admin_id:
        await update.callback_query.edit_message_text("❌ Access denied. Super Admin only.")
        return
    
    if action == "super_pending_restaurants":
        await show_pending_restaurants(update)
    elif action == "super_statistics":
        await show_system_statistics(update)
    elif action.startswith("approve_restaurant_"):
        restaurant_user_id = int(action.split("_")[-1])
        print(f"DEBUG: Processing approve_restaurant for user {restaurant_user_id}")
        logger.info(f"DEBUG: Processing approve_restaurant for user {restaurant_user_id}")
        await approve_restaurant(update, restaurant_user_id)
    elif action.startswith("reject_restaurant_"):
        restaurant_user_id = int(action.split("_")[-1])
        await reject_restaurant(update, restaurant_user_id)
    else:
        await update.callback_query.edit_message_text("🔧 Super Admin feature coming soon...")

async def show_pending_restaurants(update: Update):
    """Show pending restaurant registrations"""
    user_id = update.callback_query.from_user.id
    
    if not pending_restaurant_approvals:
        text = "📋 No pending restaurant registrations."
        keyboard = build_back_keyboard(user_id, user_languages, "back_to_super_admin")
    else:
        text = "🏢 **Pending Restaurant Registrations:**\n\n"
        for reg_user_id, data in pending_restaurant_approvals.items():
            text += f"• {data['name']} ({data['phone']})\n"
        
        keyboard = build_pending_restaurants_keyboard(user_id, pending_restaurant_approvals, user_languages)
    
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def approve_restaurant(update: Update, restaurant_user_id: int):
    """Approve restaurant registration with enhanced notifications"""
    print(f"DEBUG: approve_restaurant called for user {restaurant_user_id}")
    logger.info(f"Starting restaurant approval for user {restaurant_user_id}")
    logger.info(f"Pending approvals: {list(pending_restaurant_approvals.keys())}")
    
    print(f"DEBUG: Checking if user {restaurant_user_id} is in pending approvals")
    if restaurant_user_id in pending_restaurant_approvals:
        print(f"DEBUG: User {restaurant_user_id} found in pending approvals")
        restaurant_data = pending_restaurant_approvals[restaurant_user_id]
        logger.info(f"Restaurant data: {restaurant_data}")
        
        # Ensure user is in memory first
        ensure_user_in_memory(restaurant_user_id, storage)
        
        # Update user role
        users[restaurant_user_id]['role'] = UserRole.RESTAURANT_ADMIN
        users[restaurant_user_id]['restaurant_name'] = restaurant_data['name']
        # Ensure language/state defaults
        if restaurant_user_id not in user_languages:
            user_languages[restaurant_user_id] = 'en'
        user_states[restaurant_user_id] = UserState.IDLE
        
        # Remove from pending
        del pending_restaurant_approvals[restaurant_user_id]
        
        # Persist to DB: set role and create restaurant
        try:
            storage.set_user_role(restaurant_user_id, 'RESTAURANT_ADMIN')
            storage.upsert_user(restaurant_user_id, users.get(restaurant_user_id, {}).get('username'), None, role='RESTAURANT_ADMIN', language=user_languages.get(restaurant_user_id, 'en'), phone=restaurant_data.get('phone'))
            storage.create_restaurant_for_owner(restaurant_user_id, restaurant_data.get('name'), restaurant_data.get('phone'))
            storage.add_audit_log(user_telegram_id=update.effective_user.id if update and update.effective_user else None, action='APPROVE_RESTAURANT', target=str(restaurant_user_id), details=str(restaurant_data))
            logger.info(f"Successfully persisted restaurant approval to database")
        except Exception as e:
            logger.error(f"Persistence error approving restaurant: {e}")
        
        # Notify restaurant admin with dashboard
        try:
            from telegram import Bot
            bot = Bot(token=os.environ.get("BOT_TOKEN"))
            
            logger.info(f"Sending approval notification to {restaurant_user_id}")
            # Send approval message
            await bot.send_message(
                chat_id=restaurant_user_id,
                text=get_text(restaurant_user_id, "restaurant_approved", user_languages)
            )
            
            logger.info(f"Showing restaurant admin dashboard to {restaurant_user_id}")
            # Automatically show restaurant admin dashboard
            keyboard = build_restaurant_admin_menu_keyboard(restaurant_user_id, user_languages)
            dashboard_text = get_text(restaurant_user_id, "restaurant_admin_menu", user_languages)
            
            await bot.send_message(
                chat_id=restaurant_user_id,
                text=dashboard_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            # Fallback plain text prompt (no markdown) to ensure visibility
            await bot.send_message(
                chat_id=restaurant_user_id,
                text="Tip: If buttons are not visible, type /start to open your dashboard."
            )
            logger.info(f"Successfully sent dashboard to restaurant admin {restaurant_user_id}")
        except Exception as e:
            logger.error(f"Error notifying restaurant admin: {e}")
        
        await update.callback_query.edit_message_text(
            f"✅ Restaurant '{restaurant_data['name']}' approved successfully!"
        )
    else:
        logger.error(f"Restaurant registration not found for user {restaurant_user_id}")
        await update.callback_query.edit_message_text("❌ Restaurant registration not found.")

async def reject_restaurant(update: Update, restaurant_user_id: int):
    """Reject restaurant registration"""
    if restaurant_user_id in pending_restaurant_approvals:
        restaurant_data = pending_restaurant_approvals[restaurant_user_id]
        
        # Remove from pending
        del pending_restaurant_approvals[restaurant_user_id]
        
        # Notify user
        try:
            from telegram import Bot
            bot = Bot(token=os.environ.get("BOT_TOKEN"))
            await bot.send_message(
                chat_id=restaurant_user_id,
                text=get_text(restaurant_user_id, "restaurant_rejected", user_languages)
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        
        await update.callback_query.edit_message_text(
            f"❌ Restaurant '{restaurant_data['name']}' registration rejected."
        )
    else:
        await update.callback_query.edit_message_text("❌ Restaurant registration not found.")



async def approve_waiter(update: Update, waiter_user_id: int):
    """Approve waiter registration and notify waiter"""
    print(f"DEBUG: APPROVE_WAITER FUNCTION CALLED for user {waiter_user_id}")
    logger.info(f"DEBUG: APPROVE_WAITER FUNCTION CALLED for user {waiter_user_id}")
    print(f"DEBUG: Starting waiter approval for user {waiter_user_id}")
    logger.info(f"DEBUG: Starting waiter approval for user {waiter_user_id}")
    
    if waiter_user_id in pending_waiter_approvals:
        waiter_data = pending_waiter_approvals[waiter_user_id]
        print(f"DEBUG: Waiter data: {waiter_data}")
        logger.info(f"DEBUG: Waiter data: {waiter_data}")
        
        # Update role
        users.setdefault(waiter_user_id, {'id': waiter_user_id, 'username': None, 'role': UserRole.NEW_USER, 'restaurant_id': None, 'waiter_id': None, 'created_at': None})
        users[waiter_user_id]['role'] = UserRole.WAITER
        # Remove from pending
        del pending_waiter_approvals[waiter_user_id]
        
        # Persist to DB: set role and create waiter record linked to restaurant
        try:
            # Get the restaurant admin who approved this waiter
            approving_admin_id = update.effective_user.id if update and update.effective_user else None
            restaurant = storage.get_restaurant_by_owner(approving_admin_id) if approving_admin_id else None
            restaurant_id = restaurant.get('id') if restaurant else None
            
            storage.set_user_role(waiter_user_id, 'WAITER')
            storage.upsert_user(waiter_user_id, users.get(waiter_user_id, {}).get('username'), None, role='WAITER', language=user_languages.get(waiter_user_id, 'en'), phone=waiter_data.get('phone'))
            storage.create_waiter_for_user(waiter_user_id, restaurant_id=restaurant_id)
            storage.add_audit_log(user_telegram_id=approving_admin_id, action='APPROVE_WAITER', target=str(waiter_user_id), details=str(waiter_data))
            print(f"DEBUG: Successfully persisted waiter approval to database with restaurant_id={restaurant_id}")
            logger.info(f"DEBUG: Successfully persisted waiter approval to database with restaurant_id={restaurant_id}")
        except Exception as e:
            print(f"DEBUG: Persistence error approving waiter: {e}")
            logger.error(f"Persistence error approving waiter: {e}")
        
        # Notify waiter
        try:
            from telegram import Bot
            bot = Bot(token=os.environ.get("BOT_TOKEN"))
            # Ensure language default for waiter
            if waiter_user_id not in user_languages:
                user_languages[waiter_user_id] = 'en'
            
            print(f"DEBUG: Sending approval notification to waiter {waiter_user_id}")
            logger.info(f"DEBUG: Sending approval notification to waiter {waiter_user_id}")
            
            await bot.send_message(chat_id=waiter_user_id, text=get_text(waiter_user_id, "waiter_approved", user_languages))
            
            # Show waiter menu
            keyboard = build_waiter_menu_keyboard(waiter_user_id, user_languages)
            await bot.send_message(chat_id=waiter_user_id, text=get_text(waiter_user_id, "waiter_menu", user_languages), reply_markup=keyboard, parse_mode='Markdown')
            
            print(f"DEBUG: Successfully sent dashboard to waiter {waiter_user_id}")
            logger.info(f"DEBUG: Successfully sent dashboard to waiter {waiter_user_id}")
        except Exception as e:
            print(f"DEBUG: Error notifying waiter: {e}")
            logger.error(f"Error notifying waiter: {e}")
        
        await show_waiter_management(update)
    else:
        print(f"DEBUG: Waiter registration not found for user {waiter_user_id}")
        logger.error(f"Waiter registration not found for user {waiter_user_id}")
        await update.callback_query.edit_message_text("❌ Waiter registration not found.")

async def reject_waiter(update: Update, waiter_user_id: int):
    """Reject waiter registration and notify waiter"""
    print(f"DEBUG: Starting waiter rejection for user {waiter_user_id}")
    logger.info(f"DEBUG: Starting waiter rejection for user {waiter_user_id}")
    
    if waiter_user_id in pending_waiter_approvals:
        waiter_data = pending_waiter_approvals[waiter_user_id]
        del pending_waiter_approvals[waiter_user_id]
        
        # Notify waiter
        try:
            from telegram import Bot
            bot = Bot(token=os.environ.get("BOT_TOKEN"))
            if waiter_user_id not in user_languages:
                user_languages[waiter_user_id] = 'en'
            await bot.send_message(chat_id=waiter_user_id, text=get_text(waiter_user_id, "waiter_rejected", user_languages))
        except Exception as e:
            logger.error(f"Error notifying waiter: {e}")
        
        await show_waiter_management(update)
    else:
        await update.callback_query.edit_message_text("❌ Waiter registration not found.")
async def show_system_statistics(update: Update):
    """Show system statistics"""
    user_id = update.callback_query.from_user.id
    
    total_users = len(users)
    total_restaurants = len([u for u in users.values() if u['role'] == UserRole.RESTAURANT_ADMIN])
    total_waiters = len([u for u in users.values() if u['role'] == UserRole.WAITER])
    pending_restaurants = len(pending_restaurant_approvals)
    pending_waiters = len(pending_waiter_approvals)
    
    text = (
        f"📊 **System Statistics**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🏢 Restaurants: {total_restaurants}\n"
        f"👨‍🍳 Waiters: {total_waiters}\n"
        f"⏳ Pending Restaurant Approvals: {pending_restaurants}\n"
        f"⏳ Pending Waiter Approvals: {pending_waiters}\n"
    )
    
    keyboard = build_back_keyboard(user_id, user_languages, "back_to_super_admin")
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')



async def handle_waiter_action(update: Update, action: str):
    """Handle Waiter actions
    PRD:M1.2 Waiter capture and transactions
    """
    user_id = update.callback_query.from_user.id
    
    ensure_user_in_memory(user_id, storage)
    if users[user_id]['role'] != UserRole.WAITER:
        await update.callback_query.edit_message_text("❌ Access denied. Waiter only.")
        return
    
    if action == "waiter_capture_payment":
        await start_payment_capture(update)
    elif action == "waiter_transactions":
        await show_waiter_transactions(update, page=0)
    elif action.startswith("tx_page_"):
        new_page = int(action.split("_")[-1])
        await show_waiter_transactions(update, page=new_page)
    elif action == "waiter_help":
        await show_waiter_help(update)
    elif action.startswith("restaurant_tx_page_"):
        new_page = int(action.split("_")[-1])
        await show_restaurant_transactions(update, page=new_page)
    elif action == "view_restaurant_waiters":
        await show_restaurant_waiters(update)
    elif action == "download_daily_report":
        await handle_download_daily_report(update)
    elif action == "manage_waiters":
        await show_pending_waiter_requests(update)

    else:
        await update.callback_query.edit_message_text("👤 Waiter feature coming soon...")

async def show_waiter_transactions(update: Update, page: int = 0):
    """Show waiter transaction history with pagination"""
    user_id = update.callback_query.from_user.id
    
    # Get waiter ID for this user
    waiter = storage.get_waiter_by_user_telegram(user_id)
    if not waiter:
        await update.callback_query.edit_message_text("❌ Waiter profile not found.")
        return
    
    PAGE_SIZE = 20
    offset = page * PAGE_SIZE

    # Get transactions for this waiter
    transactions = storage.list_transactions_by_waiter(waiter['id'], limit=PAGE_SIZE, offset=offset)
    total_count = storage.count_transactions_by_waiter(waiter['id'])
    
    if not transactions:
        text = "📒 **My Transactions**\n\nNo transactions found yet. Start capturing payments to see your transaction history here."
    else:
        text = f"📒 **My Transactions**\n\n"
        text += f"**Page {page+1} of {(total_count + PAGE_SIZE - 1) // PAGE_SIZE}**\n"
        text += f"**Total: {total_count} transactions**\n\n"
        for tx in transactions:
            text += f"💰 **{tx.get('amount', 'N/A')} ETB**\n"
            text += f"🏦 Bank: {tx.get('bank_name', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n"
            text += f"📄 Receipt: {tx.get('receipt_number', 'N/A')}\n\n"
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"tx_page_{page-1}"))
    if len(transactions) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"tx_page_{page+1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")])

    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_waiter_help(update: Update):
    """Show waiter help information"""
    user_id = update.callback_query.from_user.id
    
    text = "❓ **Waiter Help**\n\n"
    text += "**How to capture payments:**\n"
    text += "1. Click '📸 Capture Payment'\n"
    text += "2. Select the bank (CBE, Telebirr, etc.)\n"
    text += "3. Take a clear photo of the receipt\n"
    text += "4. The system will extract payment details\n\n"
    text += "**Tips for better OCR:**\n"
    text += "• Ensure good lighting\n"
    text += "• Keep receipt flat and straight\n"
    text += "• Avoid shadows and glare\n"
    text += "• Make sure text is clearly visible\n\n"
    text += "**Viewing transactions:**\n"
    text += "• Click '📒 My Transactions' to see your payment history\n"
    text += "• All captured payments are automatically saved\n\n"
    text += "**Need more help?**\n"
    text += "Contact your restaurant admin for assistance."
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
async def handle_restaurant_admin_action(update: Update, action: str):
    """Handle Restaurant Admin actions
    PRD:M1.3 Manage waiters; Rules: waiter ≠ admin
    """
    user_id = update.callback_query.from_user.id
    
    ensure_user_in_memory(user_id, storage)
    if users[user_id]['role'] != UserRole.RESTAURANT_ADMIN:
        await update.callback_query.edit_message_text("❌ Access denied. Restaurant Admin only.")
        return
    
    if action == "restaurant_manage_waiters":
        await show_waiter_management(update)
    else:
        await update.callback_query.edit_message_text("🏪 Restaurant Admin feature coming soon...")

async def show_waiter_management(update: Update):
    """Show waiter management interface
    PRD:M1.3 Pending waiter approvals
    """
    user_id = update.callback_query.from_user.id
    
    if not pending_waiter_approvals:
        text = "👥 **Waiter Management**\n\n📋 No pending waiter registrations."
        keyboard = build_back_keyboard(user_id, user_languages, "back_to_restaurant_admin")
    else:
        text = "👥 **Waiter Management**\n\n📋 **Pending Waiter Registrations:**\n\n"
        keyboard = []
        
        for waiter_user_id, waiter_data in pending_waiter_approvals.items():
            text += f"👤 **Waiter:** {waiter_data.get('name', 'Unknown')}\n"
            text += f"📞 **Phone:** {waiter_data.get('phone', 'Not provided')}\n"
            text += f"🆔 **User ID:** {waiter_user_id}\n\n"
            
            # Add approval/rejection buttons
            keyboard.append([
                InlineKeyboardButton("✅ Approve", callback_data=f"restaurant_approve_waiter_{waiter_user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"restaurant_reject_waiter_{waiter_user_id}")
            ])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")])
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')



async def handle_restaurant_admin_action(update: Update, action: str):
    """Handle Restaurant Admin actions
    PRD:M1.3 Manage waiters; Rules: waiter ≠ admin
    """
    user_id = update.callback_query.from_user.id
    
    ensure_user_in_memory(user_id, storage)
    if users[user_id]['role'] != UserRole.RESTAURANT_ADMIN:
        await update.callback_query.edit_message_text("❌ Access denied. Restaurant Admin only.")
        return
    
    if action == "restaurant_manage_waiters":
        await show_waiter_management(update)
    elif action == "restaurant_transactions":
        await show_restaurant_transactions(update)
    elif action == "restaurant_settings":
        await show_restaurant_settings(update)
    elif action == "restaurant_upload_statement":
        await handle_upload_statement(update)
    elif action == "restaurant_reconciliation":
        await handle_reconciliation(update)
    else:
        await update.callback_query.edit_message_text("🏪 Restaurant Admin feature coming soon...")

async def show_restaurant_transactions(update: Update, page: int = 0):
    """Show restaurant transaction history"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get transactions for this restaurant
    PAGE_SIZE = 20
    offset = page * PAGE_SIZE
    transactions = storage.list_transactions_by_restaurant(restaurant['id'], limit=PAGE_SIZE, offset=offset)
    total_count = storage.count_transactions_by_restaurant(restaurant['id'])
    
    if not transactions:
        text = "📒 **Restaurant Transactions**\n\nNo transactions found for your restaurant yet."
    else:
        text = f"📒 **Restaurant Transactions**\n\n"
        text += f"**Page {page+1} of {(total_count + PAGE_SIZE - 1) // PAGE_SIZE}**\n"
        text += f"**Total: {total_count} transactions**\n\n"
        for tx in transactions:
            text += f"💰 **{tx.get('amount', 'N/A')} ETB**\n"
            text += f"🏦 Bank: {tx.get('bank_name', 'Unknown')}\n"
            text += f"👤 Waiter: {tx.get('waiter_name', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n\n"
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"restaurant_tx_page_{page-1}"))
    if len(transactions) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"restaurant_tx_page_{page+1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("👥 View Waiters", callback_data="view_restaurant_waiters")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_restaurant_settings(update: Update):
    """Show restaurant settings"""
    user_id = update.callback_query.from_user.id
    
    text = "⚙️ **Restaurant Settings**\n\n"
    text += "• Restaurant Name: [Your Restaurant]\n"
    text += "• Phone: [Your Phone]\n"
    text += "• Status: Active\n\n"
    text += "Settings management coming soon..."
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"restaurant_tx_page_{page-1}"))
    if len(transactions) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"restaurant_tx_page_{page+1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("👥 View Waiters", callback_data="view_restaurant_waiters")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_restaurant_reconciliation(update: Update):
    """Show restaurant reconciliation (placeholder)"""
    user_id = update.callback_query.from_user.id
    
    text = "🔄 **Make Reconciliation**\n\n"
    text += "This feature will allow you to reconcile payments with your bank statements.\n\n"
    text += "**Coming Soon:**\n"
    text += "• Upload bank statement\n"
    text += "• Match transactions\n"
    text += "• Generate reconciliation report\n\n"
    text += "This feature is planned for future releases."
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"restaurant_tx_page_{page-1}"))
    if len(transactions) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"restaurant_tx_page_{page+1}"))

    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("👥 View Waiters", callback_data="view_restaurant_waiters")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
def create_application(token: str):
    app = ApplicationBuilder().token(token).build()
    
    # Add global error handler
    app.add_error_handler(error_handler)
    global storage, ocr
    storage = Storage(os.environ.get("DATABASE_URL", "sqlite:///veripay_dev.db"))
    ocr = VisionOCR()
    
    # Create database tables
    storage.create_tables()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    app.add_handler(CommandHandler("menu", show_home))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document_upload))    
    if LEGACY_UI:
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Health check command


    app.add_handler(CommandHandler("health", health_command))


    
    return app


# ----------------------
# M1 & M2 Enhancement Functions (Non-Breaking)
# ----------------------

async def show_restaurant_waiters(update: Update):
    """Show all waiters for a restaurant - NEW FUNCTION"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get waiters for this restaurant
    waiters = storage.list_waiters_by_restaurant(restaurant["id"])
    
    if not waiters:
        text = "👥 **Restaurant Waiters**\n\nNo waiters assigned to your restaurant yet."
    else:
        text = f"👥 **Restaurant Waiters**\n\n**Total: {len(waiters)} waiters**\n\n"
        
        for waiter in waiters:
            # Get transaction count for this waiter
            tx_count = storage.count_transactions_by_waiter(waiter["id"])
            text += f"👤 **{waiter.get(full_name, waiter.get(username, "Unknown"))}**\n"
            text += f"📱 ID: {waiter.get(telegram_id, "N/A")}\n"
            text += f"📊 Transactions: {tx_count}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Transactions", callback_data="restaurant_transactions")],
        [InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]
    ]
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=Markdown)

async def handle_download_daily_report(update: Update):
    """Handle daily report download - NEW FUNCTION"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    try:
        # Generate PDF
        pdf_generator = PDFGenerator(storage)
        pdf_data = pdf_generator.generate_daily_report(restaurant["id"])
        
        # Send PDF
        filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        await update.callback_query.message.reply_document(
            document=pdf_data,
            filename=filename,
            caption=f"📄 Daily Report - {restaurant["name"]}\nDate: {datetime.now().strftime('%B %d, %Y')}"
        )
        
        # Show success message
        await update.callback_query.answer("✅ Report generated successfully!")
        
    except Exception as e:
        await update.callback_query.answer(f"❌ Error generating report: {str(e)}")

async def show_pending_waiter_requests(update: Update):
    """Show pending waiter requests for approval - NEW FUNCTION"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get pending requests
    requests = storage.get_pending_waiter_requests(restaurant["id"])
    
    if not requests:
        text = "👥 **Pending Waiter Requests**\n\nNo pending requests at this time."
    else:
        text = f"👥 **Pending Waiter Requests**\n\n**Total: {len(requests)} requests**\n\n"
        
        for req in requests:
            text += f"👤 **{req.get(full_name, req.get(username, "Unknown"))}**\n"
            text += f"📱 ID: {req.get(telegram_id, "N/A")}\n"
            text += f"🏪 Restaurant: {req.get(restaurant_name, "Unknown")}\n"
            text += f"📅 Requested: {req.get(created_at, "Unknown")}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]
    ]
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=Markdown)

if __name__ == "__main__":
    # Debug environment variables
    print("=== ENVIRONMENT VARIABLES DEBUG ===")
    use_webhook_val = os.environ.get("USE_WEBHOOK", "NOT_SET")
    public_url_val = os.environ.get("PUBLIC_URL", "NOT_SET")
    port_val = os.environ.get("PORT", "NOT_SET")
    webhook_path_val = os.environ.get("WEBHOOK_PATH", "NOT_SET")
    bot_token_val = os.environ.get("BOT_TOKEN", "NOT_SET")
    if bot_token_val != "NOT_SET":
        bot_token_val = bot_token_val[:10] + "..."
    print(f"USE_WEBHOOK: {repr(use_webhook_val)}")
    print(f"PUBLIC_URL: {repr(public_url_val)}")
    print(f"PORT: {repr(port_val)}")
    print(f"WEBHOOK_PATH: {repr(webhook_path_val)}")
    print(f"BOT_TOKEN: {repr(bot_token_val)}")
    print("=== END DEBUG ===")
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    app = create_application(token)
    print("Bot is running! Press Ctrl+C to stop.")
    use_webhook = os.environ.get("USE_WEBHOOK", "0") == "1"
    print(f"use_webhook evaluated to: {use_webhook}")
    if use_webhook:
        public_url = os.environ.get("PUBLIC_URL")
        webhook_path = os.environ.get("WEBHOOK_PATH", "/webhook")
        port = int(os.environ.get("PORT", "10000"))
        if not public_url:
            raise ValueError("PUBLIC_URL must be set when USE_WEBHOOK=1")
        print(f"Starting webhook mode on port {port} with URL {public_url}{webhook_path}")
        app.run_webhook(listen="0.0.0.0", port=port, url_path=webhook_path, webhook_url=f"{public_url}{webhook_path}")
    else:
        print("Starting polling mode")
        app.run_polling()
