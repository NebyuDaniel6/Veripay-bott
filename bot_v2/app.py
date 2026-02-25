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
        await show_waiter_transactions(update, page=0)
    elif action.startswith("tx_page_"):
        # Handle pagination
        page = int(action.split("_")[-1])
        await show_waiter_transactions(update, page=page)
    elif action == "waiter_help":
        await show_waiter_help(update)
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
            text += f"🏦 Bank: {tx.get('bank', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n"
            text += f"📄 Ref: {tx.get('original_ref', tx.get('transaction_id', 'N/A'))}\n\n"
    
    # Pagination navigation
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
        await show_restaurant_transactions(update, page=0)
    elif action.startswith("restaurant_tx_page_"):
        # Handle pagination
        page = int(action.split("_")[-1])
        await show_restaurant_transactions(update, page=page)
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
    elif action == "restaurant_transaction_management":
        await show_transaction_management(update)
    elif action == "restaurant_daily_reports":
        await show_daily_reports(update)
    elif action == "view_all_transactions":
        await show_paginated_transactions(update, page=0, filter_type="all")
    elif action == "view_pending_transactions":
        await show_paginated_transactions(update, page=0, filter_type="pending")
    elif action == "view_verified_transactions":
        await show_paginated_transactions(update, page=0, filter_type="verified")
    elif action.startswith("transactions_"):
        # Handle paginated transaction views
        parts = action.split("_")
        if len(parts) >= 3:
            filter_type = parts[1]
            page = int(parts[2])
            await show_paginated_transactions(update, page=page, filter_type=filter_type)
    elif action.startswith("verify_tx_"):
        # Handle transaction verification
        transaction_id = int(action.split("_")[-1])
        await verify_transaction(update, transaction_id)
    elif action == "export_transactions":
        await export_transactions_csv(update, filter_type="all")
    elif action.startswith("export_"):
        # Handle export with filters
        if action.startswith("export_verified"):
            await export_transactions_csv(update, filter_type="verified")
        elif action.startswith("export_pending"):
            await export_transactions_csv(update, filter_type="pending")
        else:
            await export_transactions_csv(update, filter_type="all")
    elif action.startswith("daily_report_"):
        # Handle daily report requests
        date = action.split("_")[-1]
        await show_daily_report_detail(update, date)
    elif action == "waiter_performance_report":
        await show_waiter_performance_report(update)
    elif action == "export_daily_report":
        await export_daily_report_csv(update)
    elif action.startswith("export_daily_"):
        # Handle daily report export
        date = action.split("_")[-1]
        await export_daily_report_csv(update, date)
    elif action == "export_waiter_performance":
        await export_waiter_performance_csv(update)
    elif action.startswith("weekly_report_"):
        day = action.split("_")[-1]
        is_last_week = (day == "lastweek")
        await show_weekly_day_report(update, day, is_last_week)
    elif action == "export_all_weekly":
        await export_weekly_transactions(update)
    elif action.startswith("export_weekly_"):
        # Handle weekly export for specific day
        parts = action.split("_")
        if len(parts) >= 4:
            day = parts[2]
            week_offset = int(parts[3])
            await export_weekly_day_transactions(update, day, week_offset)
    else:
        await update.callback_query.edit_message_text("🏪 Restaurant Admin feature coming soon...")

async def show_restaurant_transactions(update: Update, page: int = 0):
    """Show restaurant transaction history with pagination"""
    user_id = update.callback_query.from_user.id
    
    # Get restaurant ID for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    PAGE_SIZE = 20
    offset = page * PAGE_SIZE
    
    # Get transactions for this restaurant
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
            text += f"🏦 Bank: {tx.get('bank', 'Unknown')}\n"
            text += f"👤 Waiter ID: {tx.get('waiter_id', 'Unknown')}\n"
            text += f"📅 Date: {tx.get('created_at', 'Unknown')}\n\n"
    
    # Pagination navigation
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"restaurant_tx_page_{page-1}"))
    if len(transactions) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"restaurant_tx_page_{page+1}"))
    
    keyboard = []
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")])
    
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


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
async def show_transaction_management(update: Update):
    """Show transaction management dashboard for restaurant admin"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get basic stats
    total_transactions = storage.count_transactions_by_restaurant(restaurant['id'])
    verified_transactions = storage.count_transactions_by_restaurant_with_filters(
        restaurant['id'], verified_only=True
    )
    unverified_transactions = total_transactions - verified_transactions
    
    text = f"📒 **Transaction Management** - {restaurant['name']}\n\n"
    text += f"📊 **Summary:**\n"
    text += f"• Total Transactions: {total_transactions}\n"
    text += f"• ✅ Verified: {verified_transactions}\n"
    text += f"• ⏳ Pending: {unverified_transactions}\n\n"
    text += "Choose an action:"
    
    keyboard = [
        [InlineKeyboardButton("📅 Monday Report", callback_data="weekly_report_monday")],
        [InlineKeyboardButton("📅 Tuesday Report", callback_data="weekly_report_tuesday")],
        [InlineKeyboardButton("📅 Wednesday Report", callback_data="weekly_report_wednesday")],
        [InlineKeyboardButton("📅 Thursday Report", callback_data="weekly_report_thursday")],
        [InlineKeyboardButton("📅 Friday Report", callback_data="weekly_report_friday")],
        [InlineKeyboardButton("📅 Saturday Report", callback_data="weekly_report_saturday")],
        [InlineKeyboardButton("📅 Sunday Report", callback_data="weekly_report_sunday")],
        [InlineKeyboardButton("📊 Last Week", callback_data="weekly_report_lastweek")],
        [InlineKeyboardButton("📤 Export All", callback_data="export_all_weekly")],
        [InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def show_daily_reports(update: Update):
    """Show daily reports dashboard for restaurant admin"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Auto-archive old transactions (older than 2 weeks)
    archived_count = await check_and_archive_old_transactions(restaurant['id'])
    if archived_count > 0:
        logger.info(f"Auto-archived {archived_count} old transactions for restaurant {restaurant['id']}")
    
    # Get today's date
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get today's summary
    summary = storage.get_daily_transaction_summary(restaurant['id'], today)
    
    text = f"📊 **Daily Reports** - {restaurant['name']}\n\n"
    text += f"📅 **Today ({today}):**\n"
    text += f"• Total Transactions: {summary.get('total_transactions', 0)}\n"
    text += f"• Total Amount: {summary.get('total_amount', 0):.2f} ETB\n"
    text += f"• Verified: {summary.get('verified_transactions', 0)} ({summary.get('verified_amount', 0):.2f} ETB)\n"
    text += f"• Pending: {summary.get('unverified_transactions', 0)} ({summary.get('unverified_amount', 0):.2f} ETB)\n\n"
    
    if summary.get('waiter_breakdown'):
        text += "👥 **Waiter Performance Today:**\n"
        for waiter in summary['waiter_breakdown'][:5]:  # Show top 5
            text += f"• {waiter['waiter_name']}: {waiter['transaction_count']} txns, {waiter['total_amount']:.2f} ETB\n"
        text += "\n"
    
    text += "Choose an action:"
    
    keyboard = [
        [InlineKeyboardButton("📅 Weekly Reports", callback_data="restaurant_transaction_management")],
        [InlineKeyboardButton("📅 Today's Report", callback_data=f"daily_report_{today}")],
        [InlineKeyboardButton("📊 Custom Date Range", callback_data="custom_daily_report")],
        [InlineKeyboardButton("👥 Waiter Performance", callback_data="waiter_performance_report")],
        [InlineKeyboardButton("📤 Export Daily Report", callback_data="export_daily_report")],
        [InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def show_paginated_transactions(update: Update, page: int = 0, filter_type: str = "all"):
    """Show paginated transactions with verification status"""
    user_id = update.effective_user.id
    PAGE_SIZE = 10
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Determine filters
    verified_only = None
    if filter_type == "verified":
        verified_only = True
    elif filter_type == "pending":
        verified_only = False
    
    # Get transactions
    offset = page * PAGE_SIZE
    transactions = storage.list_transactions_by_restaurant_with_filters(
        restaurant['id'], verified_only=verified_only, limit=PAGE_SIZE, offset=offset
    )
    
    total_count = storage.count_transactions_by_restaurant_with_filters(
        restaurant['id'], verified_only=verified_only
    )
    
    text = f"📒 **Transactions** - {restaurant['name']}\n\n"
    text += f"Filter: {filter_type.title()} | Page {page + 1}/{(total_count + PAGE_SIZE - 1) // PAGE_SIZE}\n\n"
    
    if not transactions:
        text += "No transactions found.\n"
    else:
        for tx in transactions:
            status_icon = "✅" if tx.get('verified') else "⏳"
            verified_info = f" (Verified by {tx.get('verified_by_name', 'Unknown')})" if tx.get('verified') else ""
            text += f"{status_icon} **{tx['amount']} ETB** - {tx.get('waiter_name', 'Unknown')}{verified_info}\n"
            text += f"   Bank: {tx.get('bank', 'Unknown')} | {tx.get('created_at', '')[:10]}\n\n"
    
    # Build navigation buttons
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"transactions_{filter_type}_{page-1}"))
    if offset + PAGE_SIZE < total_count:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"transactions_{filter_type}_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add verification buttons for unverified transactions
    if transactions and filter_type in ["all", "pending"]:
        verify_buttons = []
        for tx in transactions:
            if not tx.get('verified'):
                verify_buttons.append(InlineKeyboardButton(
                    f"✅ Verify {tx['amount']} ETB", 
                    callback_data=f"verify_tx_{tx['id']}"
                ))
                if len(verify_buttons) >= 3:  # Limit to 3 buttons per row
                    keyboard.append(verify_buttons)
                    verify_buttons = []
        if verify_buttons:
            keyboard.append(verify_buttons)
    
    # Filter buttons
    filter_buttons = []
    if filter_type != "all":
        filter_buttons.append(InlineKeyboardButton("📋 All", callback_data="transactions_all_0"))
    if filter_type != "pending":
        filter_buttons.append(InlineKeyboardButton("⏳ Pending", callback_data="transactions_pending_0"))
    if filter_type != "verified":
        filter_buttons.append(InlineKeyboardButton("✅ Verified", callback_data="transactions_verified_0"))
    if filter_buttons:
        keyboard.append(filter_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Transaction Management", callback_data="restaurant_transaction_management")])
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def verify_transaction(update: Update, transaction_id: int):
    """Verify a transaction"""
    user_id = update.effective_user.id
    
    # Get the transaction
    transaction = storage.get_transaction_by_id(transaction_id)
    if not transaction:
        await update.callback_query.answer("❌ Transaction not found")
        return
    
    # Check if user is restaurant admin for this transaction
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant or transaction['restaurant_id'] != restaurant['id']:
        await update.callback_query.answer("❌ You don't have permission to verify this transaction")
        return
    
    # Verify the transaction
    success = storage.verify_transaction(transaction_id, user_id, "Verified by restaurant admin")
    
    if success:
        await update.callback_query.answer("✅ Transaction verified successfully!")
        # Refresh the current view
        await show_paginated_transactions(update, page=0, filter_type="all")
    else:
        await update.callback_query.answer("❌ Failed to verify transaction")

async def export_transactions_csv(update: Update, filter_type: str = "all", date_from: str = None, date_to: str = None):
    """Export transactions to CSV format"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Determine filters
    verified_only = None
    if filter_type == "verified":
        verified_only = True
    elif filter_type == "pending":
        verified_only = False
    
    # Get all transactions matching the filter
    transactions = storage.list_transactions_by_restaurant_with_filters(
        restaurant['id'], verified_only=verified_only, date_from=date_from, date_to=date_to, limit=10000
    )
    
    if not transactions:
        await update.callback_query.answer("❌ No transactions to export")
        return
    
    # Create CSV content
    csv_content = "Transaction ID,Amount,Currency,Bank,Waiter,Status,Verified By,Date,Time,Payer,Receiver,Reference\n"
    
    for tx in transactions:
        status = "Verified" if tx.get('verified') else "Pending"
        verified_by = tx.get('verified_by_name', '') if tx.get('verified') else ''
        csv_content += f"{tx['id']},{tx['amount']},{tx.get('currency', 'ETB')},{tx.get('bank', '')},{tx.get('waiter_name', '')},{status},{verified_by},{tx.get('created_at', '')[:10]},{tx.get('created_at', '')[11:19]},{tx.get('payer', '')},{tx.get('receiver', '')},{tx.get('original_ref', '')}\n"
    
    # Send as document
    from io import BytesIO
    from datetime import datetime
    buf = BytesIO(csv_content.encode('utf-8'))
    buf.name = f"transactions_{filter_type}_{restaurant['name']}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await update.callback_query.message.reply_document(
        document=buf,
        caption=f"📊 Exported {len(transactions)} transactions ({filter_type})"
    )
    
    await update.callback_query.answer("✅ Export completed!")

async def show_daily_report_detail(update: Update, date: str):
    """Show detailed daily report for a specific date"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get daily summary
    summary = storage.get_daily_transaction_summary(restaurant['id'], date)
    
    text = f"📊 **Daily Report** - {restaurant['name']}\n"
    text += f"📅 **Date:** {date}\n\n"
    
    text += f"📈 **Summary:**\n"
    text += f"• Total Transactions: {summary.get('total_transactions', 0)}\n"
    text += f"• Total Amount: {summary.get('total_amount', 0):.2f} ETB\n"
    text += f"• Verified: {summary.get('verified_transactions', 0)} ({summary.get('verified_amount', 0):.2f} ETB)\n"
    text += f"• Pending: {summary.get('unverified_transactions', 0)} ({summary.get('unverified_amount', 0):.2f} ETB)\n\n"
    
    if summary.get('waiter_breakdown'):
        text += "👥 **Waiter Performance:**\n"
        for waiter in summary['waiter_breakdown']:
            verification_rate = (waiter['verified_count'] / waiter['transaction_count'] * 100) if waiter['transaction_count'] > 0 else 0
            text += f"• **{waiter['waiter_name']}:**\n"
            text += f"  - {waiter['transaction_count']} transactions, {waiter['total_amount']:.2f} ETB\n"
            text += f"  - {waiter['verified_count']} verified ({verification_rate:.1f}%)\n"
        text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("📤 Export This Report", callback_data=f"export_daily_{date}")],
        [InlineKeyboardButton("🔙 Back to Daily Reports", callback_data="restaurant_daily_reports")]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def show_waiter_performance_report(update: Update):
    """Show waiter performance summary"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get waiter performance (last 30 days)
    from datetime import datetime, timedelta
    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    performance = storage.get_waiter_performance_summary(restaurant['id'], date_from=date_from)
    
    text = f"👥 **Waiter Performance Report** - {restaurant['name']}\n"
    text += f"📅 **Period:** Last 30 days\n\n"
    
    if not performance:
        text += "No waiter performance data available.\n"
    else:
        for waiter in performance:
            text += f"• **{waiter['waiter_name']}:**\n"
            text += f"  - {waiter['total_transactions']} transactions\n"
            text += f"  - {waiter['total_amount']:.2f} ETB total\n"
            text += f"  - {waiter['avg_transaction_amount']:.2f} ETB average\n"
            text += f"  - {waiter['verification_rate']:.1f}% verification rate\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📤 Export Performance Report", callback_data="export_waiter_performance")],
        [InlineKeyboardButton("🔙 Back to Daily Reports", callback_data="restaurant_daily_reports")]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def export_daily_report_csv(update: Update, date: str = None):
    """Export daily report to CSV"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    if not date:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
    
    # Get daily summary
    summary = storage.get_daily_transaction_summary(restaurant['id'], date)
    
    # Create CSV content
    csv_content = f"Daily Report for {restaurant['name']} - {date}\n\n"
    csv_content += "Summary\n"
    csv_content += f"Total Transactions,{summary.get('total_transactions', 0)}\n"
    csv_content += f"Total Amount,{summary.get('total_amount', 0):.2f} ETB\n"
    csv_content += f"Verified Transactions,{summary.get('verified_transactions', 0)}\n"
    csv_content += f"Verified Amount,{summary.get('verified_amount', 0):.2f} ETB\n"
    csv_content += f"Pending Transactions,{summary.get('unverified_transactions', 0)}\n"
    csv_content += f"Pending Amount,{summary.get('unverified_amount', 0):.2f} ETB\n\n"
    
    if summary.get('waiter_breakdown'):
        csv_content += "Waiter Breakdown\n"
        csv_content += "Waiter,Transactions,Total Amount,Verified Count,Verified Amount\n"
        for waiter in summary['waiter_breakdown']:
            csv_content += f"{waiter['waiter_name']},{waiter['transaction_count']},{waiter['total_amount']:.2f},{waiter['verified_count']},{waiter['verified_amount']:.2f}\n"
    
    # Send as document
    from io import BytesIO
    buf = BytesIO(csv_content.encode('utf-8'))
    buf.name = f"daily_report_{restaurant['name']}_{date}.csv"
    
    await update.callback_query.message.reply_document(
        document=buf,
        caption=f"📊 Daily Report for {date}"
    )
    
    await update.callback_query.answer("✅ Daily report exported!")

async def export_waiter_performance_csv(update: Update):
    """Export waiter performance report to CSV"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get waiter performance (last 30 days)
    from datetime import datetime, timedelta
    date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    performance = storage.get_waiter_performance_summary(restaurant['id'], date_from=date_from)
    
    if not performance:
        await update.callback_query.answer("❌ No performance data to export")
        return
    
    # Create CSV content
    csv_content = f"Waiter Performance Report for {restaurant['name']} - Last 30 Days\n\n"
    csv_content += "Waiter,Total Transactions,Total Amount,Average Transaction,Verified Transactions,Verified Amount,Verification Rate\n"
    
    for waiter in performance:
        csv_content += f"{waiter['waiter_name']},{waiter['total_transactions']},{waiter['total_amount']:.2f},{waiter['avg_transaction_amount']:.2f},{waiter['verified_transactions']},{waiter['verified_amount']:.2f},{waiter['verification_rate']:.1f}%\n"
    
    # Send as document
    from io import BytesIO
    buf = BytesIO(csv_content.encode('utf-8'))
    buf.name = f"waiter_performance_{restaurant['name']}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await update.callback_query.message.reply_document(
        document=buf,
        caption=f"📊 Waiter Performance Report (Last 30 Days)"
    )
    
    await update.callback_query.answer("✅ Performance report exported!")

async def show_weekly_day_report(update: Update, day_name: str, is_last_week: bool = False):
    """Show detailed report for specific weekday or last week"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get transactions for the specified day/week
    week_offset = -1 if is_last_week else 0
    transactions = storage.get_transactions_by_weekday(restaurant['id'], day_name, week_offset)
    
    # Calculate date range for display
    from datetime import datetime, timedelta
    today = datetime.now()
    days_since_monday = today.weekday()
    monday_of_week = today - timedelta(days=days_since_monday)
    target_week_monday = monday_of_week + timedelta(weeks=week_offset)
    
    if is_last_week:
        start_date = target_week_monday
        end_date = start_date + timedelta(days=6)
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        title = f"📊 **Last Week Report** - {restaurant['name']}"
    else:
        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        day_offset = weekday_map.get(day_name.lower(), 0)
        target_date = target_week_monday + timedelta(days=day_offset)
        date_range = target_date.strftime('%Y-%m-%d')
        title = f"📅 **{day_name.title()} Report** - {restaurant['name']}"
    
    text = f"{title}\n"
    text += f"📅 **Date:** {date_range}\n"
    text += f"🏪 **Restaurant:** {restaurant['name']}\n"
    text += f"📊 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if not transactions:
        text += "❌ **No transactions found for this period.**\n\n"
        text += "This could mean:\n"
        text += "• No transactions were recorded on this day\n"
        text += "• Transactions are older than 2 weeks (archived)\n"
        text += "• Date range is in the future\n\n"
    else:
        # Calculate comprehensive summary
        total_amount = sum(float(tx.get('amount', 0)) for tx in transactions)
        verified_count = sum(1 for tx in transactions if tx.get('verified'))
        pending_count = len(transactions) - verified_count
        verified_amount = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('verified'))
        pending_amount = total_amount - verified_amount
        
        # Bank breakdown
        bank_totals = {}
        waiter_totals = {}
        for tx in transactions:
            bank = tx.get('bank', 'Unknown')
            waiter = tx.get('waiter_name', 'Unknown')
            amount = float(tx.get('amount', 0))
            
            bank_totals[bank] = bank_totals.get(bank, 0) + amount
            waiter_totals[waiter] = waiter_totals.get(waiter, 0) + amount
        
        text += f"📈 **SUMMARY STATISTICS:**\n"
        text += f"• Total Transactions: **{len(transactions)}**\n"
        text += f"• Total Amount: **{total_amount:.2f} ETB**\n"
        text += f"• ✅ Verified: {verified_count} ({verified_amount:.2f} ETB)\n"
        text += f"• ⏳ Pending: {pending_count} ({pending_amount:.2f} ETB)\n"
        text += f"• Verification Rate: {(verified_count/len(transactions)*100):.1f}%\n\n"
        
        # Bank breakdown
        text += f"🏦 **BANK BREAKDOWN:**\n"
        for bank, amount in sorted(bank_totals.items(), key=lambda x: x[1], reverse=True):
            count = sum(1 for tx in transactions if tx.get('bank') == bank)
            text += f"• {bank}: {count} transactions, {amount:.2f} ETB\n"
        text += "\n"
        
        # Waiter breakdown
        text += f"👥 **WAITER BREAKDOWN:**\n"
        for waiter, amount in sorted(waiter_totals.items(), key=lambda x: x[1], reverse=True):
            count = sum(1 for tx in transactions if tx.get('waiter_name') == waiter)
            verified_count_waiter = sum(1 for tx in transactions if tx.get('waiter_name') == waiter and tx.get('verified'))
            text += f"• {waiter}: {count} transactions, {amount:.2f} ETB ({verified_count_waiter} verified)\n"
        text += "\n"
        
        # Detailed transaction list (Telegram has a 4096 char limit – keep this safe)
        text += f"📋 **DETAILED TRANSACTIONS (first 40):**\n"
        text += "=" * 50 + "\n"
        
        max_display = 40
        for i, tx in enumerate(transactions, 1):
            if i > max_display:
                text += f"\n…and {len(transactions) - max_display} more transactions.\n"
                break
            
            status_icon = "✅" if tx.get('verified') else "⏳"
            verified_info = f" | Verified by: {tx.get('verified_by_name', 'Unknown')}" if tx.get('verified') else ""
            verification_time = f" | Verified at: {tx.get('verified_at', '')[:19]}" if tx.get('verified') else ""
            
            text += f"{i:2d}. {status_icon} **{tx['amount']} ETB**\n"
            text += f"    💳 Bank: {tx.get('bank', 'Unknown')}\n"
            text += f"    👤 Waiter: {tx.get('waiter_name', 'Unknown')}\n"
            text += f"    📅 Date: {tx.get('created_at', '')[:19]}\n"
            text += f"    🆔 ID: {tx.get('id', 'N/A')}\n"
            if tx.get('payer'):
                text += f"    💰 Payer: {tx.get('payer', '')}\n"
            if tx.get('receiver'):
                text += f"    📥 Receiver: {tx.get('receiver', '')}\n"
            if tx.get('original_ref'):
                text += f"    🔗 Reference: {tx.get('original_ref', '')}\n"
            if tx.get('verification_notes'):
                text += f"    📝 Notes: {tx.get('verification_notes', '')}\n"
            text += f"    📊 Status: {'VERIFIED' if tx.get('verified') else 'PENDING'}{verified_info}{verification_time}\n"
            text += "    " + "-" * 40 + "\n"
        
        text += f"\n📊 **REPORT SUMMARY:**\n"
        text += f"• Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"• Total transactions processed: {len(transactions)}\n"
        text += f"• Total amount processed: {total_amount:.2f} ETB\n"
        text += f"• Verification completion: {(verified_count/len(transactions)*100):.1f}%\n"
    
    # Build keyboard
    keyboard = [
        [InlineKeyboardButton("📤 Export This Report", callback_data=f"export_weekly_{day_name}_{week_offset}")],
        [InlineKeyboardButton("🔙 Back to Weekly Reports", callback_data="restaurant_transaction_management")]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def export_weekly_transactions(update: Update):
    """Export all current week transactions with comprehensive details"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get all transactions for current week (Monday to Sunday)
    transactions = storage.get_transactions_by_weekday(restaurant['id'], 'lastweek', week_offset=0)
    
    if not transactions:
        await update.callback_query.answer("❌ No transactions to export for current week")
        return
    
    # Calculate summary statistics
    total_amount = sum(float(tx.get('amount', 0)) for tx in transactions)
    verified_count = sum(1 for tx in transactions if tx.get('verified'))
    pending_count = len(transactions) - verified_count
    verified_amount = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('verified'))
    pending_amount = total_amount - verified_amount
    
    # Create comprehensive CSV content
    from datetime import datetime
    csv_content = f"Weekly Transaction Report - {restaurant['name']}\n"
    csv_content += f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    csv_content += f"Report Period: Current Week (Monday to Sunday)\n\n"
    
    # Summary section
    csv_content += "SUMMARY STATISTICS\n"
    csv_content += f"Total Transactions,{len(transactions)}\n"
    csv_content += f"Total Amount (ETB),{total_amount:.2f}\n"
    csv_content += f"Verified Transactions,{verified_count}\n"
    csv_content += f"Verified Amount (ETB),{verified_amount:.2f}\n"
    csv_content += f"Pending Transactions,{pending_count}\n"
    csv_content += f"Pending Amount (ETB),{pending_amount:.2f}\n"
    csv_content += f"Verification Rate (%),{(verified_count/len(transactions)*100):.1f}\n\n"
    
    # Bank breakdown
    bank_totals = {}
    for tx in transactions:
        bank = tx.get('bank', 'Unknown')
        amount = float(tx.get('amount', 0))
        bank_totals[bank] = bank_totals.get(bank, 0) + amount
    
    csv_content += "BANK BREAKDOWN\n"
    csv_content += "Bank,Transaction Count,Total Amount (ETB)\n"
    for bank, amount in sorted(bank_totals.items(), key=lambda x: x[1], reverse=True):
        count = sum(1 for tx in transactions if tx.get('bank') == bank)
        csv_content += f"{bank},{count},{amount:.2f}\n"
    csv_content += "\n"
    
    # Waiter breakdown
    waiter_totals = {}
    for tx in transactions:
        waiter = tx.get('waiter_name', 'Unknown')
        amount = float(tx.get('amount', 0))
        waiter_totals[waiter] = waiter_totals.get(waiter, 0) + amount
    
    csv_content += "WAITER BREAKDOWN\n"
    csv_content += "Waiter,Transaction Count,Total Amount (ETB),Verified Count,Verified Amount (ETB)\n"
    for waiter, amount in sorted(waiter_totals.items(), key=lambda x: x[1], reverse=True):
        count = sum(1 for tx in transactions if tx.get('waiter_name') == waiter)
        verified_count_waiter = sum(1 for tx in transactions if tx.get('waiter_name') == waiter and tx.get('verified'))
        verified_amount_waiter = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('waiter_name') == waiter and tx.get('verified'))
        csv_content += f"{waiter},{count},{amount:.2f},{verified_count_waiter},{verified_amount_waiter:.2f}\n"
    csv_content += "\n"
    
    # Detailed transactions
    csv_content += "DETAILED TRANSACTIONS\n"
    csv_content += "Transaction ID,Amount (ETB),Currency,Bank,Waiter,Status,Verified By,Verified At,Date,Time,Payer,Receiver,Reference,Verification Notes\n"
    
    for tx in transactions:
        status = "VERIFIED" if tx.get('verified') else "PENDING"
        verified_by = tx.get('verified_by_name', '') if tx.get('verified') else ''
        verified_at = tx.get('verified_at', '')[:19] if tx.get('verified') else ''
        verification_notes = tx.get('verification_notes', '').replace(',', ';') if tx.get('verification_notes') else ''
        
        csv_content += f"{tx['id']},{tx['amount']},{tx.get('currency', 'ETB')},{tx.get('bank', '')},{tx.get('waiter_name', '')},{status},{verified_by},{verified_at},{tx.get('created_at', '')[:10]},{tx.get('created_at', '')[:19]},{tx.get('payer', '')},{tx.get('receiver', '')},{tx.get('original_ref', '')},{verification_notes}\n"
    
    # Send as document
    from io import BytesIO
    from datetime import datetime
    buf = BytesIO(csv_content.encode('utf-8'))
    buf.name = f"weekly_report_{restaurant['name']}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    await update.callback_query.message.reply_document(
        document=buf,
        caption=f"📊 Weekly Report - {len(transactions)} transactions"
    )
    
    await update.callback_query.answer("✅ Weekly report exported!")

async def export_weekly_day_transactions(update: Update, day_name: str, week_offset: int):
    """Export transactions for a specific day with comprehensive details"""
    user_id = update.effective_user.id
    
    # Get restaurant for this admin
    restaurant = storage.get_restaurant_by_owner(user_id)
    if not restaurant:
        await update.callback_query.edit_message_text("❌ Restaurant not found.")
        return
    
    # Get transactions for the specified day
    transactions = storage.get_transactions_by_weekday(restaurant['id'], day_name, week_offset)
    
    if not transactions:
        await update.callback_query.answer("❌ No transactions to export for this day")
        return
    
    # Calculate date range for display
    from datetime import datetime, timedelta
    today = datetime.now()
    days_since_monday = today.weekday()
    monday_of_week = today - timedelta(days=days_since_monday)
    target_week_monday = monday_of_week + timedelta(weeks=week_offset)
    
    if day_name == 'lastweek':
        start_date = target_week_monday
        end_date = start_date + timedelta(days=6)
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        title = f"Last Week Report - {restaurant['name']}"
    else:
        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        day_offset = weekday_map.get(day_name.lower(), 0)
        target_date = target_week_monday + timedelta(days=day_offset)
        date_range = target_date.strftime('%Y-%m-%d')
        title = f"{day_name.title()} Report - {restaurant['name']}"
    
    # Calculate summary statistics
    total_amount = sum(float(tx.get('amount', 0)) for tx in transactions)
    verified_count = sum(1 for tx in transactions if tx.get('verified'))
    pending_count = len(transactions) - verified_count
    verified_amount = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('verified'))
    pending_amount = total_amount - verified_amount
    
    # Create comprehensive CSV content
    csv_content = f"{title}\n"
    csv_content += f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    csv_content += f"Report Period: {date_range}\n\n"
    
    # Summary section
    csv_content += "SUMMARY STATISTICS\n"
    csv_content += f"Total Transactions,{len(transactions)}\n"
    csv_content += f"Total Amount (ETB),{total_amount:.2f}\n"
    csv_content += f"Verified Transactions,{verified_count}\n"
    csv_content += f"Verified Amount (ETB),{verified_amount:.2f}\n"
    csv_content += f"Pending Transactions,{pending_count}\n"
    csv_content += f"Pending Amount (ETB),{pending_amount:.2f}\n"
    csv_content += f"Verification Rate (%),{(verified_count/len(transactions)*100):.1f}\n\n"
    
    # Bank breakdown
    bank_totals = {}
    for tx in transactions:
        bank = tx.get('bank', 'Unknown')
        amount = float(tx.get('amount', 0))
        bank_totals[bank] = bank_totals.get(bank, 0) + amount
    
    csv_content += "BANK BREAKDOWN\n"
    csv_content += "Bank,Transaction Count,Total Amount (ETB)\n"
    for bank, amount in sorted(bank_totals.items(), key=lambda x: x[1], reverse=True):
        count = sum(1 for tx in transactions if tx.get('bank') == bank)
        csv_content += f"{bank},{count},{amount:.2f}\n"
    csv_content += "\n"
    
    # Waiter breakdown
    waiter_totals = {}
    for tx in transactions:
        waiter = tx.get('waiter_name', 'Unknown')
        amount = float(tx.get('amount', 0))
        waiter_totals[waiter] = waiter_totals.get(waiter, 0) + amount
    
    csv_content += "WAITER BREAKDOWN\n"
    csv_content += "Waiter,Transaction Count,Total Amount (ETB),Verified Count,Verified Amount (ETB)\n"
    for waiter, amount in sorted(waiter_totals.items(), key=lambda x: x[1], reverse=True):
        count = sum(1 for tx in transactions if tx.get('waiter_name') == waiter)
        verified_count_waiter = sum(1 for tx in transactions if tx.get('waiter_name') == waiter and tx.get('verified'))
        verified_amount_waiter = sum(float(tx.get('amount', 0)) for tx in transactions if tx.get('waiter_name') == waiter and tx.get('verified'))
        csv_content += f"{waiter},{count},{amount:.2f},{verified_count_waiter},{verified_amount_waiter:.2f}\n"
    csv_content += "\n"
    
    # Detailed transactions
    csv_content += "DETAILED TRANSACTIONS\n"
    csv_content += "Transaction ID,Amount (ETB),Currency,Bank,Waiter,Status,Verified By,Verified At,Date,Time,Payer,Receiver,Reference,Verification Notes\n"
    
    for tx in transactions:
        status = "VERIFIED" if tx.get('verified') else "PENDING"
        verified_by = tx.get('verified_by_name', '') if tx.get('verified') else ''
        verified_at = tx.get('verified_at', '')[:19] if tx.get('verified') else ''
        verification_notes = tx.get('verification_notes', '').replace(',', ';') if tx.get('verification_notes') else ''
        
        csv_content += f"{tx['id']},{tx['amount']},{tx.get('currency', 'ETB')},{tx.get('bank', '')},{tx.get('waiter_name', '')},{status},{verified_by},{verified_at},{tx.get('created_at', '')[:10]},{tx.get('created_at', '')[:19]},{tx.get('payer', '')},{tx.get('receiver', '')},{tx.get('original_ref', '')},{verification_notes}\n"
    
    # Send as document
    from io import BytesIO
    buf = BytesIO(csv_content.encode('utf-8'))
    buf.name = f"{day_name}_report_{restaurant['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    await update.callback_query.message.reply_document(
        document=buf,
        caption=f"📊 {day_name.title()} Report for {date_range}"
    )
    
    await update.callback_query.answer("✅ Day report exported!")

async def check_and_archive_old_transactions(restaurant_id: int):
    """Auto-archive transactions older than 2 weeks"""
    archived_count = storage.archive_old_transactions(restaurant_id, weeks_old=2)
    if archived_count > 0:
        logger.info(f"Auto-archived {archived_count} transactions for restaurant {restaurant_id}")
    return archived_count

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
        rows = [["Date/Time", "Transaction Number", "Amount", "Waiter", "Status", "Matched Ref", "Matched Amount"]]
        for tx in bot_transactions:
            tx_id = tx.get('id')
            dt = tx.get('created_at') or f"{tx.get('transaction_date','')} {tx.get('transaction_time','')}".strip()
            tx_ref = (tx.get('transaction_id') or tx.get('original_ref') or '').upper()
            tx_amt = tx.get('amount') or ''
            
            # Get waiter information
            waiter_info = "Unknown"
            if tx.get('waiter_id'):
                waiter = storage.get_waiter_by_id(tx['waiter_id'])
                if waiter and waiter.get('user_id'):
                    user = storage.get_user_by_id(waiter['user_id'])
                    if user:
                        waiter_info = user.get('full_name') or user.get('username') or f"W{waiter['id']}"
                    else:
                        waiter_info = f"W{waiter['id']}"
            
            if tx_id in matched_map:
                ln = matched_map[tx_id]
                rows.append([dt, tx_ref, tx_amt, waiter_info, "Matched", (ln.get('reference') or '').upper(), ln.get('credit_amount') or ''])
            else:
                rows.append([dt, tx_ref, tx_amt, waiter_info, "Unmatched", "", ""])
        rows += [["","","","","","",""], 
                 ["Summary","Matched refs", str(len(matched)), "", "Matched amounts", str(len(matched)), ""],
                 ["","Unmatched refs", str(len(unmatched_bot)), "", "Unmatched amounts", str(len(unmatched_bot)), ""],
                 ["","Unmatched (Bank)", str(len(bank_unmatched)), "", "", "", ""]]
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
    """Download weekly report and archive transactions"""
    try:
        user_id = update.effective_user.id
        restaurant = storage.get_restaurant_by_owner(user_id)
        if not restaurant:
            await update.callback_query.answer("❌ Restaurant not found")
            return
        
        # Get all active (non-archived) transactions
        transactions = storage.list_transactions_by_restaurant(restaurant['id'], limit=10000, include_archived=False)
        
        if not transactions:
            await update.callback_query.answer("❌ No active transactions to export")
            return
        
        # Generate weekly report PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from datetime import datetime
        import io
        
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"Weekly Report - {restaurant.get('name','Restaurant')}", styles['Heading1']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Total Transactions: {len(transactions)}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Calculate totals
        total_amount = sum(float(tx.get('amount', 0) or 0) for tx in transactions)
        story.append(Paragraph(f"**Total Amount: {total_amount:.2f} ETB**", styles['Heading3']))
        story.append(Spacer(1, 12))
        
        # Transaction table
        rows = [["Date", "Tx Number", "Amount (ETB)", "Waiter", "Bank"]]
        for tx in transactions:
            dt = tx.get('created_at', 'N/A')
            tx_ref = tx.get('transaction_id') or tx.get('original_ref') or 'N/A'
            amount = tx.get('amount', 'N/A')
            
            # Get waiter info
            waiter_info = "Unknown"
            if tx.get('waiter_id'):
                waiter = storage.get_waiter_by_id(tx['waiter_id'])
                if waiter and waiter.get('user_id'):
                    user = storage.get_user_by_id(waiter['user_id'])
                    if user:
                        waiter_info = user.get('full_name') or user.get('username') or f"W{waiter['id']}"
            
            bank = tx.get('bank', 'N/A')
            rows.append([dt[:16] if dt else 'N/A', tx_ref, amount, waiter_info, bank])
        
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
        ]))
        story.append(table)
        
        doc.build(story)
        buf.seek(0)
        
        # Send the report
        await update.callback_query.message.reply_document(
            document=buf,
            filename=f"weekly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            caption=f"📊 Weekly Report\n\n✅ {len(transactions)} transactions\n💰 Total: {total_amount:.2f} ETB\n\n⚠️ These transactions will be archived after download."
        )
        
        # Archive the transactions
        archived_count = storage.archive_restaurant_transactions(restaurant['id'])
        
        await update.callback_query.edit_message_text(
            f"✅ Weekly report generated!\n\n"
            f"📄 {len(transactions)} transactions exported\n"
            f"📦 {archived_count} transactions archived\n\n"
            f"You can now start fresh for the new week! 🎉"
        )
        
    except Exception as e:
        logger.error(f"Weekly report error: {e}")
        await update.callback_query.answer("❌ Report generation failed")

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

# Force redeploy Tue Sep 30 19:39:56 EAT 2025
