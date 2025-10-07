import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging
import os
from io import BytesIO
from typing import Tuple, Dict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from bot_v2.state import StateStore
from bot_v2.storage import Storage
from bot_v2.ocr import VisionOCR

# Import legacy UI if enabled
LEGACY_UI = os.environ.get("LEGACY_UI", "0") == "1"
if LEGACY_UI:
    from bot_v2.ui_legacy import (
        LANGUAGES, UserRole, UserState, BANK_BUTTONS,
        get_text, build_language_selection_keyboard, build_main_menu_keyboard,
        build_super_admin_menu_keyboard, build_restaurant_admin_menu_keyboard,
        build_waiter_menu_keyboard, build_bank_selection_keyboard,
        build_payment_result_keyboard, build_pending_restaurants_keyboard,
        build_back_keyboard
    )

def ensure_user_in_memory(user_id: int, storage: Storage) -> None:
    """Ensure user is loaded from database into memory"""
    if user_id not in users:
        db_user = storage.get_user_by_telegram(user_id)
        if db_user:
            users[user_id] = {
                'id': user_id,
                'username': db_user.get('username', 'Unknown'),
                'role': getattr(UserRole, db_user.get('role', 'NEW_USER'), UserRole.NEW_USER),
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
storage = Storage(os.environ.get("DATABASE_URL", "sqlite:///veripay_dev.db"))
ocr = VisionOCR()
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
        if update.message:
            await update.message.reply_text("Welcome to VeriPay. Use menu buttons.", reply_markup=InlineKeyboardMarkup(buttons))
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
        
        # Route to appropriate dashboard based on role (persist role, no re-registration)
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

async def handle_logout(update: Update):
    """Handle logout - reset user state and show main menu"""
    user_id = update.effective_user.id
    
    # Clear user state and role from memory
    if user_id in users:
        del users[user_id]
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_languages:
        del user_languages[user_id]
    
    # Show main menu for re-registration
    await show_main_menu(update)

async def handle_login(update: Update):
    """Handle login - restore user session from database"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    super_admin_id = int(os.environ.get("SUPER_ADMIN_ID", "0") or 0)
    
    # Check if user exists in database
    db_user = storage.get_user_by_telegram(user_id)
    
    if not db_user:
        # User not found in database
        await update.callback_query.answer("❌ No account found. Please register first.", show_alert=True)
        return
    
    # Get user role
    role = db_user.get('role', 'NEW_USER')
    
    # Prevent login if user hasn't completed registration
    if role == 'NEW_USER':
        await update.callback_query.answer("❌ Please complete registration first.", show_alert=True)
        return
    
    # Restore user to memory
    try:
        user_role = getattr(UserRole, role, UserRole.NEW_USER)
    except (KeyError, AttributeError):
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
    user_states[user_id] = UserState.IDLE
    
    # Route to appropriate dashboard based on role
    if role == 'SUPER_ADMIN' or user_id == super_admin_id:
        await setup_persistent_keyboard(update, user_id, 'SUPER_ADMIN')
        await update.callback_query.answer("✅ Logged in as Super Admin", show_alert=False)
    elif role == 'RESTAURANT_ADMIN':
        await setup_persistent_keyboard(update, user_id, 'RESTAURANT_ADMIN')
        await update.callback_query.answer("✅ Logged in as Restaurant Admin", show_alert=False)
    elif role == 'WAITER':
        await setup_persistent_keyboard(update, user_id, 'WAITER')
        await update.callback_query.answer("✅ Logged in as Waiter", show_alert=False)
    else:
        await update.callback_query.answer("❌ Invalid role. Please contact support.", show_alert=True)

async def show_language_selection(update: Update):
    """Show language selection menu"""
    keyboard = build_language_selection_keyboard()
    text = LANGUAGES["en"]["welcome"]
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_main_menu(update: Update):
    """Show main registration menu"""
    user_id = update.effective_user.id
    keyboard = build_main_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "main_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_super_admin_menu(update: Update):
    """Show Super Admin menu"""
    user_id = update.effective_user.id
    keyboard = build_super_admin_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "super_admin_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_restaurant_admin_menu(update: Update):
    """Show Restaurant Admin menu"""
    user_id = update.effective_user.id
    keyboard = build_restaurant_admin_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "restaurant_admin_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def show_waiter_menu(update: Update):
    """Show Waiter menu"""
    user_id = update.effective_user.id
    keyboard = build_waiter_menu_keyboard(user_id, user_languages)
    text = get_text(user_id, "waiter_menu", user_languages)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

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
    
    # Login
    if data == "login":
        await handle_login(update)
        return
    
    # Change language
    # Logout
    if data == "logout":
        await handle_logout(update)
        return
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
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')


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
    # If already a waiter, route to dashboard (no re-registration)
    db_user = storage.get_user_by_telegram(user_id)
    if db_user and db_user.get('role') == 'WAITER':
        await setup_persistent_keyboard(update, user_id, 'WAITER')
        return
    # Prompt for restaurant id or name
    user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_SELECTION
    await update.callback_query.edit_message_text(
        "Please enter your Restaurant ID (e.g., 001, 002) or exact Restaurant Name:",
        parse_mode='Markdown'
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on user state"""
    if not LEGACY_UI:
        return  # Simple UI doesn't handle text messages
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state_name = user_states.get(user_id, UserState.IDLE)
    
    if state_name == UserState.WAITING_FOR_RESTAURANT_SELECTION:
        # Try to resolve restaurant by ID or Name
        restaurant = None
        if text.isdigit():
            restaurant = storage.get_restaurant_by_id(int(text))
        if not restaurant:
            # Try exact name match (case-insensitive)
            # For minimal change, do a simple scan of latest restaurants via owner linkage
            # If storage has a helper, prefer it; else fallback to None
            pass
        if not restaurant:
            await update.message.reply_text("❌ Restaurant not found. Please enter a valid ID or exact Name.")
            return
        # Stash selection and ask waiter name
        if 'temp_registrations' not in globals():
            globals()['temp_registrations'] = {}
        temp_registrations[user_id] = { 'restaurant_id': restaurant['id'] }
        user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        await update.message.reply_text(get_text(user_id, "waiter_name_prompt", user_languages))
        return

    elif state_name == UserState.WAITING_FOR_RESTAURANT_NAME:
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
            
            # Link to selected restaurant if provided
            selected_restaurant_id = waiter_data.get('restaurant_id')
            # Add to pending approvals (key by user id)
            pending_waiter_approvals[user_id] = waiter_data
            
            await update.message.reply_text(get_text(user_id, "registration_submitted", user_languages))
            
            # Clean up
            del temp_registrations[user_id]
            user_states[user_id] = UserState.IDLE
        return

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
            # Prefer transaction id across banks
            ref = (
                ocr_result.get("transaction_id")
                or ocr_result.get("reference")
                or ocr_result.get("original_ref")
                or ""
            )
            
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
            
            
            # Telebirr-specific formatting
            if (bank or '').lower().startswith('tele'):
                # Sanitize sender; map to 'To'
                to_val = sender
                if not to_val or any(x in (to_val or '').lower() for x in ['transaction', 'number', 'download', 'share']):
                    to_val = 'Unknown'
                parts = [
                    get_text(user_id, "captured", user_languages) if LEGACY_UI else "✅ Captured",
                    f"- Bank: {bank}",
                    f"- Amount: {amount} ETB" if amount != "Unknown" else "- Amount: Unknown",
                ]
                if ref:
                    parts.append(f"- Transaction Number: {ref}")
                parts.append(f"- To: {to_val}")
                if time_val and time_val != "Unknown":
                    parts.append(f"- Time: {time_val}")
                message_text = "\n".join(parts)
            else:
                result_parts = [
                    get_text(user_id, "captured", user_languages) if LEGACY_UI else "✅ Captured",
                    f"- Bank: {bank}",
                    f"- Amount: {amount} ETB" if amount != "Unknown" else "- Amount: Unknown",
                    f"- Sender: {sender}",
                ]
                if ref:
                    result_parts.append(f"- Transaction ID: {ref}")
                if time_val and time_val != "Unknown":
                    result_parts.append(f"- Time: {time_val}")
                message_text = "\n".join(result_parts)

            # Build keyboard for result message
            if LEGACY_UI:
                keyboard = build_payment_result_keyboard(user_id, user_languages)
            else:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔎 View Full OCR", callback_data="view_full_ocr")]])

            await update.message.reply_text(
                message_text,
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
        await show_waiter_transactions(update)
    elif action == "waiter_help":
        await show_waiter_help(update)
    else:
        await update.callback_query.edit_message_text("👤 Waiter feature coming soon...")

async def show_waiter_transactions(update: Update):
    """Show waiter transaction history"""
    user_id = update.callback_query.from_user.id
    
    # Get waiter ID for this user
    waiter = storage.get_waiter_by_user_telegram(user_id)
    if not waiter:
        await update.callback_query.edit_message_text("❌ Waiter profile not found.")
        return
    
    # Get transactions for this waiter
    transactions = storage.list_transactions_by_waiter(waiter['id'], limit=20)
    
    if not transactions:
        text = "📒 **My Transactions**\n\nNo transactions found yet. Start capturing payments to see your transaction history here."
    else:
        text = f"📒 **My Transactions**\n\n**Recent Transactions:**\n\n"
        for tx in transactions[:10]:  # Show last 10
            text += f"💰 **{tx.get('amount', 'N/A')} ETB**\n"
            text += f"🏦 Bank: {tx.get('bank_name', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n"
            text += f"📄 Receipt: {tx.get('receipt_number', 'N/A')}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")]]
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
        keyboard = build_back_keyboard(user_id, user_languages, "back_to_restaurant_admin").inline_keyboard
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
    elif action == "restaurant_reconciliation":
        await show_restaurant_reconciliation(update)
    elif action == "restaurant_recon_upload":
        await start_statement_upload(update)
    elif action == "restaurant_recon_run":
        await run_reconciliation(update)
    elif action == "restaurant_recon_download":
        await download_last_report(update)
    else:
        await update.callback_query.edit_message_text("🏪 Restaurant Admin feature coming soon...")

async def show_restaurant_transactions(update: Update):
    """Show restaurant transaction history"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get transactions for this restaurant
    transactions = storage.list_transactions_by_restaurant(restaurant['id'], limit=20)
    
    if not transactions:
        text = "📒 **Restaurant Transactions**\n\nNo transactions found for your restaurant yet."
    else:
        text = f"📒 **Restaurant Transactions**\n\n**Recent Transactions:**\n\n"
        for tx in transactions[:10]:  # Show last 10
            text += f"💰 **{tx.get('amount', 'N/A')} ETB**\n"
            text += f"🏦 Bank: {tx.get('bank_name', 'Unknown')}\n"
            text += f"👤 Waiter: {tx.get('waiter_name', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n\n"
    
    # Minimal back button without changing other flows
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]])
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)


async def show_restaurant_settings(update: Update):
    """Show restaurant settings"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant data
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text(
            "❌ Restaurant not found. Please contact support.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")
            ]])
        )
        return
    
    # Format restaurant ID with leading zeros (001, 002, etc.)
    restaurant_id = restaurant["id"]
    restaurant_id_formatted = f"{restaurant_id:03d}"
    
    # Extract restaurant data
    restaurant_name = restaurant.get("name", "Not set")
    restaurant_phone = restaurant.get("phone", "Not set")
    
    text = "⚙️ **Restaurant Settings**\n\n"
    text += f"• **Restaurant ID:** `{restaurant_id_formatted}`\n"
    text += f"• **Restaurant Name:** {restaurant_name}\n"
    text += f"• **Phone:** {restaurant_phone}\n"
    text += f"• **Status:** Active\n\n"
    text += "Share your Restaurant ID with waiters for registration."
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check endpoint"""
    await update.message.reply_text("✅ Bot is running and healthy!")

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data from Telegram Web App"""
    user_id = update.effective_user.id
    web_app_data = update.message.web_app_data
    
    if web_app_data:
        data = web_app_data.data
        await update.message.reply_text(f"📱 Received data from Web App: {data}")
    else:
        await update.message.reply_text("❌ No data received from Web App")

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
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Global error handler to avoid unhandled exceptions bubbling up
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors without logging out users"""
    try:
        logger.exception("Unhandled exception while processing update", exc_info=context.error)
        # Don't clear user state on errors - just log and continue
    except Exception:
        # Last-resort guard
        logger.exception("Unhandled exception while processing update", exc_info=context.error)
    except Exception:
        # Last-resort guard
        pass

# Reconciliation handlers (defined early to avoid NameError during registration)
async def start_statement_upload(update: Update):
    user_id = update.callback_query.from_user.id
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    await update.callback_query.edit_message_text(
        "📄 Please upload your CBE bank statement as PDF or CSV.\n- Match keys: References (transaction number) and Credit (amount)."
    )

async def handle_statement_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        return
    doc = update.message.document
    user_id = update.effective_user.id
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.message.reply_text("❌ Restaurant not found.")
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to download file: {e}")
        return

    statement_id = storage.create_bank_statement(restaurant["id"], "CBE", user_id)
    parsed = 0
    name_l = (doc.file_name or "").lower()

    if name_l.endswith(".csv"):
        import csv, io
        f = io.StringIO(file_bytes.decode("utf-8", errors="ignore"))
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            ref = (row.get("References") or row.get("Reference") or "").strip().upper()
            credit = (row.get("Credit") or row.get("Amount Credit") or "").replace(",", "").strip()
            dt = row.get("Date") or row.get("DateTime") or None
            raw = str(row)
            if not ref and not credit:
                continue
            storage.insert_bank_statement_line(statement_id, idx, dt, ref or None, credit or None, raw)
            parsed += 1
    elif name_l.endswith(".pdf"):
        # Try table extraction via pdfplumber first; fallback to PyPDF2 regex
        parsed_csv = []  # list of dicts with keys: date, reference, credit
        try:
            import pdfplumber, io, csv
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                total_tables = 0
                for page in pdf.pages:
                    tables = page.extract_tables() or []
                    total_tables += len(tables)
                    for tbl in tables:
                        if not tbl or not tbl[0]:
                            continue
                        headers = [ (h or '').strip().lower() for h in tbl[0] ]
                        # Map headers
                        def find_idx(names):
                            for i,h in enumerate(headers):
                                for n in names:
                                    if n in h:
                                        return i
                            return -1
                        idx_date = find_idx(["date", "datetime", "transaction date"])
                        idx_ref = find_idx(["reference", "reference(s)", "ref"])
                        idx_credit = find_idx(["credit", "amount credit", "cr"])
                        if idx_ref == -1 and idx_credit == -1:
                            continue
                        for row in tbl[1:]:
                            if not row:
                                continue
                            val_date = (row[idx_date] if idx_date != -1 and idx_date < len(row) else None) or ''
                            val_ref = (row[idx_ref] if idx_ref != -1 and idx_ref < len(row) else None) or ''
                            val_credit = (row[idx_credit] if idx_credit != -1 and idx_credit < len(row) else None) or ''
                            # Normalize
                            ref_norm = str(val_ref).strip().upper().replace(' ', '')
                            credit_norm = str(val_credit).replace(',', '').strip()
                            if not ref_norm and not credit_norm:
                                continue
                            parsed_csv.append({
                                'date': str(val_date).strip(),
                                'reference': ref_norm,
                                'credit': credit_norm,
                            })
                try:
                    logger.info(f"pdfplumber: tables found: {total_tables}, rows parsed: {len(parsed_csv)}")
                except Exception:
                    pass
            # Store to DB and send CSV file back
            if parsed_csv:
                import io, csv
                idx = 0
                for row in parsed_csv:
                    storage.insert_bank_statement_line(statement_id, idx, row['date'] or None, row['reference'] or None, row['credit'] or None, None)
                    parsed += 1
                    idx += 1
                # Build CSV buffer to return
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=["Date","Reference","Credit"]) 
                writer.writeheader()
                for r in parsed_csv:
                    writer.writerow({"Date": r['date'], "Reference": r['reference'], "Credit": r['credit']})
                buf.seek(0)
                await update.message.reply_document(document=io.BytesIO(buf.getvalue().encode('utf-8')), filename="statement_converted.csv", caption="✅ Converted to CSV (Date, Reference, Credit)")
            else:
                await update.message.reply_text("⚠️ No tables detected in PDF. Please upload a CSV with headers Reference(s) and Credit, or try another PDF export.")
        except Exception as e:
            # Ignore and fallback to PyPDF2 regex below
            try:
                logger.warning(f"pdfplumber failed: {e}")
            except Exception:
                pass
            pass
        if parsed == 0:
            from PyPDF2 import PdfReader
            import re, io
            reader = PdfReader(io.BytesIO(file_bytes))
            idx = 0
            for page in reader.pages:
                text = page.extract_text() or ""
                # Sliding window: pair a found CH reference with the next Credit amount within a few lines
                last_ref = None
                pending_lines = 3
                for line in text.splitlines():
                    line_stripped = line.strip()
                    # Capture reference: either labeled or bare CH code
                    m_ref = re.search(r"Reference(?:s)?[:\s]+([A-Z0-9\-]{6,})", line_stripped, re.IGNORECASE)
                    if not m_ref:
                        m_ref = re.search(r"\b(CH[A-Z0-9O]{7,})\b", line_stripped, re.IGNORECASE)
                    # Capture credit amount (labeled)
                    m_credit = re.search(r"Credit[:\s]+([0-9][\d,]*(?:\.[0-9]{2})?)", line_stripped, re.IGNORECASE)

                    if m_ref:
                        if last_ref is not None:
                            storage.insert_bank_statement_line(statement_id, idx, None, last_ref, None, "(no credit on following lines)")
                            parsed += 1
                            idx += 1
                        last_ref = m_ref.group(1).strip().upper()
                        pending_lines = 3

                    if m_credit:
                        credit_val = m_credit.group(1).replace(",", "")
                        if last_ref is not None:
                            storage.insert_bank_statement_line(statement_id, idx, None, last_ref, credit_val, line_stripped)
                            parsed += 1
                            idx += 1
                            last_ref = None
                            pending_lines = 0
                        else:
                            storage.insert_bank_statement_line(statement_id, idx, None, None, credit_val, line_stripped)
                            parsed += 1
                            idx += 1

                    if last_ref is not None:
                        pending_lines -= 1
                        if pending_lines <= 0:
                            storage.insert_bank_statement_line(statement_id, idx, None, last_ref, None, "(credit not found nearby)")
                            parsed += 1
                            idx += 1
                            last_ref = None
        # Final user feedback
        if parsed == 0:
            await update.message.reply_text("⚠️ Parsed lines: 0. Please upload a CSV with headers Reference(s) and Credit, or try another PDF export.")
        else:
            await update.message.reply_text(f"✅ Statement stored. Parsed lines: {parsed}")

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
    app.add_handler(CommandHandler("menu", show_main_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_statement_document))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    return app

async def run_reconciliation(update: Update):
    """Run reconciliation between bot transactions and bank statement"""
    try:
        user_id = update.effective_user.id
        restaurant = storage.get_restaurant_by_owner(user_id)
        if not restaurant:
            await update.callback_query.answer("❌ Restaurant not found")
            return
        
        statements = storage.list_bank_statements(restaurant['id'], "CBE", limit=1)
        if not statements:
            await update.callback_query.answer("❌ No bank statement uploaded. Please upload a statement first.")
            return
        
        latest_statement = statements[0]
        statement_lines = storage.list_bank_statement_lines(latest_statement['id'])
        if not statement_lines:
            await update.callback_query.answer("❌ No transaction lines found in statement")
            return
        
        bot_transactions = storage.list_transactions_by_restaurant(restaurant['id'], limit=1000)
        matched, unmatched_bot, bank_unmatched = [], [], []
        bot_refs = {}
        for tx in bot_transactions:
            ref = (tx.get('transaction_id') or tx.get('original_ref') or '').strip().upper()
            if ref:
                bot_refs[ref] = tx
        bank_refs = {}
        for line in statement_lines:
            ref = (line.get('reference') or '').strip().upper()
            if ref:
                bank_refs[ref] = line
        for ref, tx in bot_refs.items():
            if ref in bank_refs:
                matched.append((tx, bank_refs[ref]))
            else:
                unmatched_bot.append(tx)
        for ref, line in bank_refs.items():
            if ref not in bot_refs:
                bank_unmatched.append(line)
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(f"Reconciliation Report - {restaurant.get('name','Restaurant')} (CBE)", styles['Heading2']))
        story.append(Paragraph(f"Matched: {len(matched)} | Unmatched (Bot): {len(unmatched_bot)} | Unmatched (Bank): {len(bank_unmatched)}", styles['Normal']))
        story.append(Spacer(1, 12))
        matched_map = {tx.get('id'): ln for tx, ln in matched if tx.get('id') is not None}
        rows = [["Date/Time", "Transaction Number", "Amount", "Status", "Matched Ref", "Matched Amount"]]
        for tx in bot_transactions:
            tx_id = tx.get('id')
            dt = tx.get('created_at') or f"{tx.get('transaction_date','')} {tx.get('transaction_time','')}".strip()
            tx_ref = (tx.get('transaction_id') or tx.get('original_ref') or '').upper()
            tx_amt = tx.get('amount') or ''
            if tx_id in matched_map:
                ln = matched_map[tx_id]
                rows.append([dt, tx_ref, tx_amt, "Matched", (ln.get('reference') or '').upper(), ln.get('credit_amount') or ''])
            else:
                rows.append([dt, tx_ref, tx_amt, "Unmatched", "", ""])
        rows += [["","","","","",""], 
                 ["Summary","Matched refs", str(len(matched)), "Matched amounts", str(len(matched)), ""],
                 ["","Unmatched refs", str(len(unmatched_bot)), "Unmatched amounts", str(len(unmatched_bot)), ""],
                 ["","Unmatched (Bank)", str(len(bank_unmatched)), "", "", ""]]
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
            ('GRID',(0,0),(-1,-1),0.25,colors.grey),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('ALIGN',(2,1),(2,-1),'RIGHT'),
            ('ALIGN',(5,1),(5,-1),'RIGHT')
        ]))
        story.append(table)
        doc.build(story)
        buf.seek(0)
        await update.callback_query.message.reply_document(document=buf, filename="reconciliation_report.pdf", caption="🧾 Reconciliation Report (CBE)")
        await update.callback_query.edit_message_text("✅ Reconciliation complete. Report sent.")
    except Exception as e:
        logger.error(f"Reconciliation error: {e}")
        await update.callback_query.answer("❌ Reconciliation failed")

async def download_last_report(update: Update):
    """Download the last reconciliation report (placeholder)"""
    await update.callback_query.answer("📥 Last report download - feature coming soon!")

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

# duplicate removed; function moved above main
async def download_last_report(update: Update):
    """Download the last reconciliation report (placeholder)"""
    await update.callback_query.answer("📥 Last report download - feature coming soon!")

# Force redeploy Tue Sep 30 19:39:56 EAT 2025
