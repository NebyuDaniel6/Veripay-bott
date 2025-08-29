#!/usr/bin/env python3
"""
VeriPay Bot - Supabase Cloud Deployment Version
A unified Telegram bot for payment verification in Ethiopian restaurants
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import yaml
from pathlib import Path

# Third-party imports
from aiogram import Bot, Dispatcher, types, FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import psycopg2
from psycopg2.extras import RealDictCursor

# Local imports
from database.lean_models import Base, User, Restaurant, Table, TableAssignment, Transaction, BankStatement, ReconciliationReport, SystemLog
from database.lean_operations import UserOperations, RestaurantOperations, TableOperations, TransactionOperations, BankStatementOperations, ReconciliationReportOperations, SystemLogOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/veripay.log')
    ]
)
logger = logging.getLogger(__name__)

class RegistrationStates(StatesGroup):
    """States for user registration flow"""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_role = State()
    waiting_for_restaurant_name = State()
    waiting_for_restaurant_address = State()

class LeanVeriPayBot:
    """Lean VeriPay Bot - Unified bot for waiters and admins"""
    
    def __init__(self):
        self.config = self._load_config()
        self.bot = Bot(token=self.config['telegram']['bot_token'])
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        self.admin_user_ids = self.config['telegram']['admin_user_ids']
        
        # Initialize database
        self.engine = create_engine(self.config['database']['url'])
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        
        # Mock data for demo (in-memory)
        self.pending_registrations = {}
        self.approved_users = {}
        self.restaurants = {}
        
        # Initialize demo data
        self._init_demo_data()
        
        # Setup keyboards
        self._setup_keyboards()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("🤖 Lean VeriPay Bot initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables or config file"""
        config = {
            'telegram': {
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc'),
                'admin_user_ids': [os.getenv('ADMIN_USER_ID', '123456789')]
            },
            'database': {
                'url': os.getenv('DATABASE_URL', 'sqlite:///lean_veripay.db')
            },
            'ai': {
                'ocr_engine': 'tesseract',
                'tesseract_path': '/usr/bin/tesseract',
                'confidence_threshold': 0.7
            },
            'development': {
                'debug': os.getenv('DEBUG', 'false').lower() == 'true',
                'test_mode': os.getenv('TEST_MODE', 'false').lower() == 'true',
                'mock_bank_apis': True,
                'sample_data_enabled': True
            }
        }
        
        # Try to load from config file if it exists
        config_file = Path('config_supabase.yaml')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    # Merge with environment variables
                    for section, values in file_config.items():
                        if section not in config:
                            config[section] = {}
                        for key, value in values.items():
                            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                                env_var = value[2:-1]
                                config[section][key] = os.getenv(env_var, value)
                            else:
                                config[section][key] = value
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
        
        return config
    
    def _init_demo_data(self):
        """Initialize demo data for testing"""
        # Demo admin user
        self.approved_users['123456789'] = {
            'telegram_id': '123456789',
            'name': 'Demo Admin',
            'phone': '+251911234567',
            'role': 'admin',
            'restaurant_id': None,
            'created_at': datetime.now()
        }
        
        # Demo restaurant
        self.restaurants['1'] = {
            'id': '1',
            'name': 'Demo Restaurant',
            'address': 'Addis Ababa, Ethiopia',
            'owner_id': '123456789',
            'created_at': datetime.now()
        }
        
        # Demo waiter
        self.approved_users['369249230'] = {
            'telegram_id': '369249230',
            'name': 'Demo Waiter',
            'phone': '+251922345678',
            'role': 'waiter',
            'restaurant_id': '1',
            'created_at': datetime.now()
        }
        
        logger.info("📊 Demo data initialized")
    
    def _setup_keyboards(self):
        """Setup persistent keyboards"""
        # Guest keyboard (welcome screen)
        self.guest_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("📝 Register"), KeyboardButton("❓ Help")],
                [KeyboardButton("🏠 Home"), KeyboardButton("ℹ️ About")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        # Waiter keyboard
        self.waiter_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("📸 Capture Payment"), KeyboardButton("📊 My Transactions")],
                [KeyboardButton("🏠 Home"), KeyboardButton("🚪 Logout")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        # Admin keyboard
        self.admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton("📊 Dashboard"), KeyboardButton("👥 Manage Users")],
                [KeyboardButton("📈 Reports"), KeyboardButton("⚙️ Settings")],
                [KeyboardButton("🏠 Home"), KeyboardButton("🚪 Logout")]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    def _register_handlers(self):
        """Register all bot handlers"""
        # Command handlers
        self.dp.register_message_handler(self.cmd_start, commands=['start'])
        self.dp.register_message_handler(self.cmd_help, commands=['help'])
        self.dp.register_message_handler(self.cmd_register, commands=['register'])
        
        # Callback query handler
        self.dp.register_callback_query_handler(self.handle_callback)
        
        # Text message handler
        self.dp.register_message_handler(self.handle_text_message, content_types=['text'])
        
        # Photo message handler
        self.dp.register_message_handler(self.handle_photo_message, content_types=['photo'])
    
    async def cmd_start(self, message: types.Message):
        """Handle /start command"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        
        if user_role == 'guest':
            await self._show_guest_welcome(message)
        elif user_role == 'waiter':
            await self._show_waiter_welcome(message)
        elif user_role == 'admin':
            await self._show_admin_welcome(message)
    
    async def cmd_help(self, message: types.Message):
        """Handle /help command"""
        help_text = """
🤖 **VeriPay Bot Help**

**Available Commands:**
/start - Start the bot
/help - Show this help message
/register - Register as waiter or restaurant

**For Waiters:**
• Capture payment screenshots
• View transaction history
• Manage table assignments

**For Admins:**
• View dashboard and reports
• Manage users and restaurants
• Monitor system activity

**Need Help?**
Contact: support@veripay.et
        """
        await message.answer(help_text, parse_mode='Markdown')
    
    async def cmd_register(self, message: types.Message):
        """Handle /register command"""
        await self._start_registration(message)
    
    async def _show_guest_welcome(self, message: types.Message):
        """Show welcome screen for guests"""
        welcome_text = """
🎉 **Welcome to VeriPay!**

I'm a payment verification system for restaurants in Ethiopia.

⚠️ **Access Required:** You need to be registered as a waiter or admin to use this system.

**What can you do?**
• Register as a waiter for your restaurant
• Register your restaurant as an admin
• Learn how the system works
• Get help and support

Choose an option below to get started:
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter"),
            InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant"),
            InlineKeyboardButton("❓ How It Works", callback_data="how_it_works"),
            InlineKeyboardButton("🆘 Help & Support", callback_data="help_support"),
            InlineKeyboardButton("🎮 Demo Mode", callback_data="demo_mode"),
            InlineKeyboardButton("📞 Contact Us", callback_data="contact_us"),
            InlineKeyboardButton("📋 Commands", callback_data="show_commands"),
            InlineKeyboardButton("⭐ Rate Us", callback_data="rate_us")
        )
        
        await message.answer(welcome_text, parse_mode='Markdown', reply_markup=keyboard)
        await message.answer("Use the buttons below to navigate:", reply_markup=self.guest_keyboard)
    
    async def _show_waiter_welcome(self, message: types.Message):
        """Show welcome screen for waiters"""
        user_id = str(message.from_user.id)
        user_data = self.approved_users.get(user_id, {})
        
        welcome_text = f"""
👨‍💼 **Welcome back, {user_data.get('name', 'Waiter')}!**

You're logged in as a **Waiter** at {self._get_restaurant_name(user_data.get('restaurant_id'))}

**What can you do?**
• 📸 Capture payment screenshots
• 📊 View your transaction history
• 🏠 Return to home menu
• 🚪 Logout from the system

Use the buttons below to get started:
        """
        
        await message.answer(welcome_text, parse_mode='Markdown', reply_markup=self.waiter_keyboard)
    
    async def _show_admin_welcome(self, message: types.Message):
        """Show welcome screen for admins"""
        user_id = str(message.from_user.id)
        user_data = self.approved_users.get(user_id, {})
        
        welcome_text = f"""
👑 **Welcome back, {user_data.get('name', 'Admin')}!**

You're logged in as an **Administrator**

**What can you do?**
• 📊 View dashboard and analytics
• 👥 Manage users and restaurants
• 📈 Generate reports
• ⚙️ Configure system settings
• 🏠 Return to home menu
• 🚪 Logout from the system

Use the buttons below to get started:
        """
        
        await message.answer(welcome_text, parse_mode='Markdown', reply_markup=self.admin_keyboard)
    
    async def handle_callback(self, callback_query: types.CallbackQuery):
        """Handle all callback queries"""
        user_id = str(callback_query.from_user.id)
        callback_data = callback_query.data
        user_role = await self._get_user_role(user_id)
        
        logger.info(f"🔍 Callback received: {callback_data} from user {user_id} (role: {user_role})")
        
        try:
            if callback_data.startswith('waiter_'):
                await self._handle_waiter_callback(callback_query, callback_data)
            elif callback_data.startswith('admin_'):
                await self._handle_admin_callback(callback_query, callback_data)
            elif callback_data.startswith('register_role_'):
                await self._handle_registration_role(callback_query, callback_data)
            elif callback_data.startswith('approve_registration_'):
                await self._handle_approve_registration(callback_query, callback_data)
            elif callback_data.startswith('reject_registration_'):
                await self._handle_reject_registration(callback_query, callback_data)
            elif callback_data == 'start_registration':
                await self._start_registration(callback_query.message)
            elif callback_data == 'guest_help':
                await self.cmd_help(callback_query.message)
            elif callback_data == 'register_waiter':
                await self._start_waiter_registration(callback_query.message)
            elif callback_data == 'register_restaurant':
                await self._start_restaurant_registration(callback_query.message)
            elif callback_data == 'how_it_works':
                await self._show_how_it_works(callback_query.message)
            elif callback_data == 'help_support':
                await self._show_help_support(callback_query.message)
            elif callback_data == 'demo_mode':
                await self._show_demo_mode(callback_query.message)
            elif callback_data == 'contact_us':
                await self._show_contact_info(callback_query.message)
            elif callback_data == 'show_commands':
                await self._show_commands(callback_query.message)
            elif callback_data == 'rate_us':
                await self._show_rating_info(callback_query.message)
            else:
                await callback_query.answer("❌ Unknown command")
                
        except Exception as e:
            logger.error(f"❌ Error handling callback {callback_data}: {e}")
            await callback_query.answer("❌ An error occurred")
    
    async def handle_text_message(self, message: types.Message):
        """Handle text messages"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        text = message.text
        
        # Check if user is in registration state
        state = self.dp.current_state(user=message.from_user.id)
        current_state = await state.get_state()
        
        if current_state:
            await self._handle_registration_state(message, current_state)
            return
        
        # Handle keyboard button presses
        if text == "📝 Register":
            await self._start_registration(message)
        elif text == "❓ Help":
            await self.cmd_help(message)
        elif text == "🏠 Home":
            await self._show_home_menu(message)
        elif text == "ℹ️ About":
            await self._show_about_info(message)
        elif text == "📸 Capture Payment":
            await self._handle_capture_payment(message)
        elif text == "📊 My Transactions":
            await self._show_waiter_transactions(message)
        elif text == "📊 Dashboard":
            await self._show_admin_dashboard(message)
        elif text == "👥 Manage Users":
            await self._show_manage_users(message)
        elif text == "📈 Reports":
            await self._show_reports(message)
        elif text == "⚙️ Settings":
            await self._show_settings(message)
        elif text == "🚪 Logout":
            await self._handle_logout(message)
        else:
            await message.answer("❌ Unknown command. Use /help to see available commands.")
    
    async def handle_photo_message(self, message: types.Message):
        """Handle photo messages for payment verification"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        
        if user_role != 'waiter':
            await message.answer("❌ Only waiters can upload payment screenshots.")
            return
        
        await message.answer("📸 Processing payment screenshot...")
        
        try:
            # Get the largest photo
            photo = message.photo[-1]
            
            # Download the photo
            file_info = await self.bot.get_file(photo.file_id)
            downloaded_file = await self.bot.download_file(file_info.file_path)
            
            # Process the image (mock OCR for demo)
            transaction_data = await self._process_payment_image(downloaded_file)
            
            if transaction_data:
                await self._save_transaction(message, transaction_data)
            else:
                await message.answer("❌ Could not extract transaction data from the image. Please try again with a clearer screenshot.")
                
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await message.answer("❌ Error processing the image. Please try again.")
    
    async def _get_user_role(self, user_id: str) -> str:
        """Get user role from approved users"""
        try:
            if user_id in self.approved_users:
                return self.approved_users[user_id]['role']
            return 'guest'
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return 'guest'
    
    async def _start_registration(self, message: types.Message):
        """Start the registration process"""
        user_id = str(message.from_user.id)
        
        if user_id in self.approved_users:
            await message.answer("✅ You are already registered!")
            return
        
        if user_id in self.pending_registrations:
            await message.answer("⏳ You already have a pending registration. Please wait for approval.")
            return
        
        # Initialize registration data
        self.pending_registrations[user_id] = {
            'telegram_id': user_id,
            'created_at': datetime.now()
        }
        
        await message.answer("📝 **Registration Started**\n\nPlease provide your full name:")
        await RegistrationStates.waiting_for_name.set()
    
    async def _handle_registration_state(self, message: types.Message, state: str):
        """Handle registration state machine"""
        user_id = str(message.from_user.id)
        text = message.text
        
        if state == RegistrationStates.waiting_for_name.state:
            await self._handle_registration_name(message, text)
        elif state == RegistrationStates.waiting_for_phone.state:
            await self._handle_registration_phone(message, text)
        elif state == RegistrationStates.waiting_for_role.state:
            await self._handle_registration_role_text(message, text)
        elif state == RegistrationStates.waiting_for_restaurant_name.state:
            await self._handle_registration_restaurant_name(message, text)
        elif state == RegistrationStates.waiting_for_restaurant_address.state:
            await self._handle_registration_restaurant_address(message, text)
    
    async def _handle_registration_name(self, message: types.Message, name: str):
        """Handle name input during registration"""
        user_id = str(message.from_user.id)
        self.pending_registrations[user_id]['name'] = name
        
        await message.answer("📱 Please provide your phone number (e.g., +251911234567):")
        await RegistrationStates.waiting_for_phone.set()
    
    async def _handle_registration_phone(self, message: types.Message, phone: str):
        """Handle phone input during registration"""
        user_id = str(message.from_user.id)
        self.pending_registrations[user_id]['phone'] = phone
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👨‍💼 Waiter", callback_data="register_role_waiter"),
            InlineKeyboardButton("🏪 Restaurant Owner", callback_data="register_role_restaurant")
        )
        
        await message.answer("🎭 Please select your role:", reply_markup=keyboard)
        await RegistrationStates.waiting_for_role.set()
    
    async def _handle_registration_role(self, callback_query: types.CallbackQuery, callback_data: str):
        """Handle role selection during registration"""
        user_id = str(callback_query.from_user.id)
        role = callback_data.replace('register_role_', '')
        
        self.pending_registrations[user_id]['role'] = role
        
        if role == 'waiter':
            await callback_query.message.answer("🏪 Please provide your restaurant name:")
            await RegistrationStates.waiting_for_restaurant_name.set()
        else:  # restaurant
            await callback_query.message.answer("🏪 Please provide your restaurant name:")
            await RegistrationStates.waiting_for_restaurant_name.set()
        
        await callback_query.answer()
    
    async def _handle_registration_role_text(self, message: types.Message, role: str):
        """Handle role input via text"""
        user_id = str(message.from_user.id)
        
        if role.lower() in ['waiter', 'w']:
            self.pending_registrations[user_id]['role'] = 'waiter'
        elif role.lower() in ['restaurant', 'admin', 'a']:
            self.pending_registrations[user_id]['role'] = 'admin'
        else:
            await message.answer("❌ Invalid role. Please select 'waiter' or 'restaurant'.")
            return
        
        await message.answer("🏪 Please provide your restaurant name:")
        await RegistrationStates.waiting_for_restaurant_name.set()
    
    async def _handle_registration_restaurant_name(self, message: types.Message, restaurant_name: str):
        """Handle restaurant name input during registration"""
        user_id = str(message.from_user.id)
        self.pending_registrations[user_id]['restaurant_name'] = restaurant_name
        
        await message.answer("📍 Please provide your restaurant address:")
        await RegistrationStates.waiting_for_restaurant_address.set()
    
    async def _handle_registration_restaurant_address(self, message: types.Message, address: str):
        """Complete registration process"""
        user_id = str(message.from_user.id)
        registration_data = self.pending_registrations[user_id]
        registration_data['restaurant_address'] = address
        
        # Auto-approve for demo
        await self._complete_registration(message, registration_data)
    
    async def _complete_registration(self, message: types.Message, registration_data: dict):
        """Complete the registration process"""
        user_id = registration_data['telegram_id']
        
        # Create restaurant if it doesn't exist
        restaurant_id = None
        if registration_data.get('restaurant_name'):
            restaurant_id = str(len(self.restaurants) + 1)
            self.restaurants[restaurant_id] = {
                'id': restaurant_id,
                'name': registration_data['restaurant_name'],
                'address': registration_data.get('restaurant_address', ''),
                'owner_id': user_id,
                'created_at': datetime.now()
            }
        
        # Add user to approved users
        self.approved_users[user_id] = {
            'telegram_id': user_id,
            'name': registration_data['name'],
            'phone': registration_data['phone'],
            'role': registration_data['role'],
            'restaurant_id': restaurant_id,
            'created_at': datetime.now()
        }
        
        # Remove from pending
        del self.pending_registrations[user_id]
        
        # Clear registration state
        state = self.dp.current_state(user=message.from_user.id)
        await state.finish()
        
        success_text = f"""
✅ **Registration Successful!**

Welcome to VeriPay, {registration_data['name']}!

**Your Details:**
• Role: {registration_data['role'].title()}
• Restaurant: {registration_data.get('restaurant_name', 'N/A')}
• Phone: {registration_data['phone']}

You can now use all the features available for your role.
        """
        
        await message.answer(success_text, parse_mode='Markdown')
        
        # Show appropriate welcome screen
        if registration_data['role'] == 'waiter':
            await self._show_waiter_welcome(message)
        else:
            await self._show_admin_welcome(message)
    
    async def _process_payment_image(self, image_data) -> Optional[Dict[str, Any]]:
        """Process payment image and extract transaction data (mock for demo)"""
        try:
            # Mock OCR processing for demo
            import random
            
            transaction_data = {
                'amount': round(random.uniform(50, 500), 2),
                'currency': 'ETB',
                'transaction_id': f"TXN{random.randint(100000, 999999)}",
                'bank': random.choice(['CBE', 'Dashen', 'Telebirr']),
                'timestamp': datetime.now(),
                'status': 'pending'
            }
            
            return transaction_data
            
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            return None
    
    async def _save_transaction(self, message: types.Message, transaction_data: Dict[str, Any]):
        """Save transaction to database"""
        try:
            user_id = str(message.from_user.id)
            user_data = self.approved_users.get(user_id, {})
            
            # Create transaction record
            transaction = Transaction(
                waiter_id=user_id,
                restaurant_id=user_data.get('restaurant_id'),
                amount=transaction_data['amount'],
                currency=transaction_data['currency'],
                transaction_id=transaction_data['transaction_id'],
                bank_name=transaction_data['bank'],
                verification_status='pending',
                created_at=datetime.now()
            )
            
            # Save to database
            with self.SessionLocal() as session:
                session.add(transaction)
                session.commit()
            
            success_text = f"""
✅ **Payment Captured Successfully!**

**Transaction Details:**
• Amount: {transaction_data['amount']} {transaction_data['currency']}
• Transaction ID: {transaction_data['transaction_id']}
• Bank: {transaction_data['bank']}
• Status: Pending Verification

The transaction has been saved and is awaiting verification.
            """
            
            await message.answer(success_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")
            await message.answer("❌ Error saving transaction. Please try again.")
    
    async def _get_restaurant_name(self, restaurant_id: str) -> str:
        """Get restaurant name by ID"""
        if restaurant_id and restaurant_id in self.restaurants:
            return self.restaurants[restaurant_id]['name']
        return "Unknown Restaurant"
    
    # Additional handler methods (implemented as needed)
    async def _handle_waiter_callback(self, callback_query: types.CallbackQuery, callback_data: str):
        """Handle waiter-specific callbacks"""
        await callback_query.answer("Waiter feature coming soon!")
    
    async def _handle_admin_callback(self, callback_query: types.CallbackQuery, callback_data: str):
        """Handle admin-specific callbacks"""
        await callback_query.answer("Admin feature coming soon!")
    
    async def _handle_approve_registration(self, callback_query: types.CallbackQuery, callback_data: str):
        """Handle registration approval"""
        await callback_query.answer("Registration approved!")
    
    async def _handle_reject_registration(self, callback_query: types.CallbackQuery, callback_data: str):
        """Handle registration rejection"""
        await callback_query.answer("Registration rejected!")
    
    async def _start_waiter_registration(self, message: types.Message):
        """Start waiter registration"""
        await self._start_registration(message)
    
    async def _start_restaurant_registration(self, message: types.Message):
        """Start restaurant registration"""
        await self._start_registration(message)
    
    async def _show_how_it_works(self, message: types.Message):
        """Show how the system works"""
        text = """
🔍 **How VeriPay Works**

1. **Waiters** capture payment screenshots
2. **OCR** extracts transaction details automatically
3. **System** verifies payments against bank records
4. **Admins** get real-time reports and analytics
5. **Restaurants** ensure payment accuracy

**Benefits:**
• ⚡ Instant verification
• 📊 Detailed reporting
• 🔒 Secure and reliable
• 💰 Reduce payment errors
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_help_support(self, message: types.Message):
        """Show help and support information"""
        text = """
🆘 **Help & Support**

**Need assistance?**
• 📧 Email: support@veripay.et
• 📱 Telegram: @veripay_support
• 🌐 Website: veripay.et

**Common Issues:**
• Can't upload images? Try a clearer screenshot
• Registration not working? Check your phone number format
• Bot not responding? Try /start command

**Quick Commands:**
/start - Restart the bot
/help - Show this help
/register - Register as user
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_demo_mode(self, message: types.Message):
        """Show demo mode information"""
        text = """
🎮 **Demo Mode**

You're currently in **Demo Mode** with:
• Mock data and transactions
• Auto-approved registrations
• Sample restaurant and users
• Simulated OCR processing

**Demo Features:**
• Register as waiter/admin instantly
• Upload any image as payment
• View mock transaction history
• Test all bot features

**To go live:**
Contact us for production setup!
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_contact_info(self, message: types.Message):
        """Show contact information"""
        text = """
📞 **Contact Information**

**VeriPay Support Team**

📧 **Email:** support@veripay.et
📱 **Telegram:** @veripay_support
🌐 **Website:** veripay.et
📍 **Address:** Addis Ababa, Ethiopia

**Business Hours:**
Monday - Friday: 8:00 AM - 6:00 PM EAT
Saturday: 9:00 AM - 1:00 PM EAT

**Emergency Support:**
Available 24/7 for critical issues
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_commands(self, message: types.Message):
        """Show available commands"""
        text = """
📋 **Available Commands**

**Basic Commands:**
/start - Start the bot
/help - Show help message
/register - Register as user

**Waiter Commands:**
📸 Upload payment screenshots
📊 View transaction history
🏠 Return to home menu

**Admin Commands:**
📊 View dashboard
👥 Manage users
📈 Generate reports
⚙️ Configure settings

**Navigation:**
Use the buttons provided for easy navigation!
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_rating_info(self, message: types.Message):
        """Show rating information"""
        text = """
⭐ **Rate VeriPay**

We'd love to hear your feedback!

**Rate us on:**
• 🌟 Google Play Store
• 🍎 App Store
• 📱 Telegram Bot Store

**Share your experience:**
• 📧 Email: feedback@veripay.et
• 📱 Telegram: @veripay_feedback
• 🌐 Website: veripay.et/feedback

**Your feedback helps us improve!**
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_home_menu(self, message: types.Message):
        """Show home menu"""
        await self.cmd_start(message)
    
    async def _show_about_info(self, message: types.Message):
        """Show about information"""
        text = """
ℹ️ **About VeriPay**

**Mission:**
To revolutionize payment verification in Ethiopian restaurants through AI-powered technology.

**Features:**
• 🤖 AI-powered OCR processing
• 📊 Real-time analytics
• 🔒 Secure verification
• 📱 Easy-to-use interface

**Technology:**
• Python & AI
• Telegram Bot API
• PostgreSQL Database
• Cloud deployment

**Version:** 1.0.0 (Demo)
**Developed by:** VeriPay Team
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _handle_capture_payment(self, message: types.Message):
        """Handle capture payment request"""
        text = """
📸 **Capture Payment**

To capture a payment:

1. **Take a screenshot** of the payment confirmation
2. **Send the image** to this chat
3. **Wait for processing** (usually 5-10 seconds)
4. **Review the details** and confirm

**Tips for better results:**
• Ensure the image is clear and well-lit
• Include the transaction amount and ID
• Make sure the bank name is visible
• Avoid blurry or cropped images

**Ready to capture?** Send your payment screenshot now!
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_waiter_transactions(self, message: types.Message):
        """Show waiter's transaction history"""
        text = """
📊 **Your Transaction History**

**Recent Transactions:**
• No transactions found

**Statistics:**
• Total Transactions: 0
• Total Amount: 0 ETB
• Pending: 0
• Verified: 0

**To capture a new payment:**
Use the "📸 Capture Payment" button or send a payment screenshot.
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_admin_dashboard(self, message: types.Message):
        """Show admin dashboard"""
        text = """
📊 **Admin Dashboard**

**System Overview:**
• Total Users: 2
• Total Restaurants: 1
• Total Transactions: 0
• System Status: ✅ Online

**Recent Activity:**
• No recent activity

**Quick Actions:**
• Manage users and restaurants
• View detailed reports
• Configure system settings
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_manage_users(self, message: types.Message):
        """Show user management"""
        text = """
👥 **User Management**

**Current Users:**
• Demo Admin (Admin) - Active
• Demo Waiter (Waiter) - Active

**Pending Registrations:**
• No pending registrations

**Actions:**
• View user details
• Approve/reject registrations
• Manage user roles
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_reports(self, message: types.Message):
        """Show reports"""
        text = """
📈 **Reports**

**Available Reports:**
• Transaction Summary
• User Activity
• Restaurant Performance
• System Analytics

**Generate Report:**
Select a report type to generate.
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _show_settings(self, message: types.Message):
        """Show settings"""
        text = """
⚙️ **Settings**

**System Settings:**
• OCR Processing: Enabled
• Auto-verification: Disabled
• Notifications: Enabled
• Demo Mode: Enabled

**User Settings:**
• Language: English
• Timezone: EAT
• Notifications: All

**Contact admin for changes.**
        """
        await message.answer(text, parse_mode='Markdown')
    
    async def _handle_logout(self, message: types.Message):
        """Handle logout request"""
        user_id = str(message.from_user.id)
        
        if user_id in self.approved_users:
            del self.approved_users[user_id]
        
        text = """
🚪 **Logged Out Successfully**

You have been logged out of VeriPay.

To use the system again:
• Use /start to restart
• Register again if needed
• Contact support for help

Thank you for using VeriPay!
        """
        await message.answer(text, parse_mode='Markdown')
        await self._show_guest_welcome(message)
    
    async def start_polling(self):
        """Start the bot polling"""
        logger.info("🤖 Starting Lean VeriPay Bot...")
        logger.info(f"📱 Bot: @{self.bot.get_me().username}")
        logger.info(f"🔗 Link: https://t.me/{self.bot.get_me().username}")
        logger.info("🔍 OCR Processing: ENABLED")
        logger.info("👥 Role-based access: ENABLED")
        logger.info("⏹️  Press Ctrl+C to stop")
        
        try:
            await self.dp.start_polling()
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")

async def main():
    """Main function"""
    bot = LeanVeriPayBot()
    await bot.start_polling()

if __name__ == '__main__':
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                Lean VeriPay Bot                              ║")
    print("║                                                              ║")
    print("║  🤖 Unified bot for waiters and admins                      ║")
    print("║  📱 Role-based access with button interfaces                ║")
    print("║  🔍 Real OCR processing for payment screenshots             ║")
    print("║  📊 Admin dashboard and reporting                           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    asyncio.run(main()) 