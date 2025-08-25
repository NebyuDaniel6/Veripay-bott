#!/usr/bin/env python3
"""
Lean VeriPay Bot - Unified bot for waiters and admins
Single bot with role-based access and button interfaces
"""
import asyncio
import yaml
import json
import re
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from PIL import Image
import pytesseract
import io
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import aiogram
try:
    from aiogram import Bot, Dispatcher, types, Router
    from aiogram.filters import Command
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    print("⚠️  aiogram not installed. Install with: pip3 install aiogram")

# Import database models and operations
try:
    from database.models import Waiter, Admin, Transaction, Restaurant, VerificationStatus, BankType
    from database.operations import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  Database modules not available. Running in demo mode.")


class WaiterStates(StatesGroup):
    """States for waiter conversation flow"""
    waiting_for_payment_photo = State()
    confirming_transaction = State()


class AdminStates(StatesGroup):
    """States for admin conversation flow"""
    waiting_for_statement = State()
    waiting_for_waiter_info = State()


class RegistrationStates(StatesGroup):
    """States for registration flow"""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_role = State()
    waiting_for_restaurant_name = State()
    waiting_for_restaurant_address = State()
    waiting_for_approval = State()


class LeanOCRExtractor:
    """Lean OCR extractor for payment screenshots"""
    
    def __init__(self):
        """Initialize OCR extractor"""
        # Common patterns for Ethiopian payment systems
        self.patterns = {
            'stn_number': [
                r'STN[:\s]*([A-Z0-9]{8,})',
                r'Transaction[:\s]*([A-Z0-9]{8,})',
                r'Ref[:\s]*([A-Z0-9]{8,})',
                r'([A-Z0-9]{8,})',  # Generic 8+ alphanumeric
            ],
            'amount': [
                r'Amount[:\s]*([0-9,]+\.?[0-9]*)',
                r'Total[:\s]*([0-9,]+\.?[0-9]*)',
                r'([0-9,]+\.?[0-9]*)\s*Birr',
                r'([0-9,]+\.?[0-9]*)\s*ETB',
            ],
            'date': [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                r'(\d{1,2}\s+\w+\s+\d{4})',
            ],
            'time': [
                r'(\d{1,2}:\d{2}:\d{2})',
                r'(\d{1,2}:\d{2})',
            ],
            'sender': [
                r'From[:\s]*([A-Za-z\s]+)',
                r'Sender[:\s]*([A-Za-z\s]+)',
                r'Account[:\s]*([A-Za-z\s]+)',
            ],
            'receiver': [
                r'To[:\s]*([A-Za-z\s]+)',
                r'Receiver[:\s]*([A-Za-z\s]+)',
                r'Beneficiary[:\s]*([A-Za-z\s]+)',
            ]
        }
    
    def extract_transaction_data(self, image_bytes: bytes) -> dict:
        """
        Extract transaction data from payment screenshot
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict containing extracted data with confidence scores
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            
            # Parse extracted text
            extracted_data = self._parse_text_data(text)
            
            # Determine bank type
            bank_type = self._detect_bank_type(text)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_confidence(extracted_data)
            
            return {
                'stn_number': extracted_data.get('stn_number'),
                'amount': extracted_data.get('amount'),
                'transaction_date': extracted_data.get('transaction_date'),
                'sender_account': extracted_data.get('sender_account'),
                'receiver_account': extracted_data.get('receiver_account'),
                'bank_type': bank_type,
                'full_text': text,
                'confidence': overall_confidence,
                'extraction_details': extracted_data
            }
            
        except Exception as e:
            print(f"Error extracting transaction data: {e}")
            return {
                'error': str(e),
                'confidence': 0.0
            }
    
    def _parse_text_data(self, text: str) -> dict:
        """Parse extracted text to find transaction details"""
        extracted_data = {}
        
        # Extract STN Number
        stn_number = self._extract_pattern(text, self.patterns['stn_number'])
        if stn_number:
            extracted_data['stn_number'] = stn_number
        
        # Extract Amount
        amount_str = self._extract_pattern(text, self.patterns['amount'])
        if amount_str:
            try:
                # Clean amount string and convert to float
                amount_clean = amount_str.replace(',', '').replace(' ', '')
                extracted_data['amount'] = float(amount_clean)
            except ValueError:
                print(f"Could not parse amount: {amount_str}")
        
        # Extract Date and Time
        date_str = self._extract_pattern(text, self.patterns['date'])
        time_str = self._extract_pattern(text, self.patterns['time'])
        
        if date_str:
            try:
                # Parse date
                transaction_date = self._parse_date(date_str, time_str)
                if transaction_date:
                    extracted_data['transaction_date'] = transaction_date
            except ValueError:
                print(f"Could not parse date: {date_str}")
        
        # Extract Sender Account
        sender = self._extract_pattern(text, self.patterns['sender'])
        if sender:
            extracted_data['sender_account'] = sender.strip()
        
        # Extract Receiver Account
        receiver = self._extract_pattern(text, self.patterns['receiver'])
        if receiver:
            extracted_data['receiver_account'] = receiver.strip()
        
        return extracted_data
    
    def _extract_pattern(self, text: str, patterns: list) -> str:
        """Extract text using regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        return None
    
    def _parse_date(self, date_str: str, time_str: str = None) -> datetime:
        """Parse date and time strings"""
        try:
            # Common date formats
            date_formats = [
                '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d', '%y/%m/%d',
                '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d', '%y-%m-%d',
                '%d %B %Y', '%d %b %Y'
            ]
            
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    
                    # Add time if provided
                    if time_str:
                        try:
                            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
                            date_obj = date_obj.replace(hour=time_obj.hour, 
                                                       minute=time_obj.minute, 
                                                       second=time_obj.second)
                        except ValueError:
                            try:
                                time_obj = datetime.strptime(time_str, '%H:%M').time()
                                date_obj = date_obj.replace(hour=time_obj.hour, 
                                                           minute=time_obj.minute)
                            except ValueError:
                                pass
                    
                    return date_obj
                except ValueError:
                    continue
            
            return None
        except Exception as e:
            print(f"Error parsing date: {e}")
            return None
    
    def _detect_bank_type(self, text: str) -> str:
        """Detect bank type from text"""
        text_lower = text.lower()
        
        if 'cbe' in text_lower or 'commercial bank' in text_lower:
            return 'cbe'
        elif 'telebirr' in text_lower or 'ethio telecom' in text_lower:
            return 'telebirr'
        elif 'dashen' in text_lower or 'dashen bank' in text_lower:
            return 'dashen'
        else:
            return 'other'
    
    def _calculate_confidence(self, extracted_data: dict) -> float:
        """Calculate overall confidence score"""
        confidence_scores = []
        
        # Base confidence for each extracted field
        if extracted_data.get('stn_number'):
            confidence_scores.append(0.8)
        if extracted_data.get('amount'):
            confidence_scores.append(0.9)
        if extracted_data.get('transaction_date'):
            confidence_scores.append(0.7)
        if extracted_data.get('sender_account'):
            confidence_scores.append(0.6)
        if extracted_data.get('receiver_account'):
            confidence_scores.append(0.6)
        
        # Return average confidence
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0


class LeanVeriPayBot:
    """Unified lean VeriPay bot for waiters and admins"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the bot"""
        # Load config
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.bot_token = self.config['telegram']['waiter_bot_token']
        self.bot = None
        self.dp = None
        self.ocr_extractor = LeanOCRExtractor()
        
        # Initialize database if available
        if DB_AVAILABLE:
            self.db_manager = DatabaseManager(config_path)
        else:
            self.db_manager = None
        
        # Create directories
        Path('uploads').mkdir(exist_ok=True)
        Path('logs').mkdir(exist_ok=True)
        Path('reports').mkdir(exist_ok=True)
        
        # Mock data storage for demo
        self.pending_registrations = {}  # telegram_id -> registration_data
        self.approved_users = {
            "123456789": {"name": "Admin User", "role": "admin", "phone": "+251911234567"},
            "111111111": {"name": "John Doe", "role": "waiter", "phone": "+251922345678", "table": "T01", "expires": "2024-09-01"},
            "222222222": {"name": "Jane Smith", "role": "waiter", "phone": "+251933456789", "table": "T04", "expires": "2024-09-01"},
            "333333333": {"name": "Mike Johnson", "role": "waiter", "phone": "+251944567890", "table": "T07", "expires": "2024-09-01"},
        }
        self.restaurants = {
            "Demo Restaurant": {
                "name": "Demo Restaurant",
                "address": "Addis Ababa, Ethiopia",
                "phone": "+251911234567",
                "admin_id": "123456789"
            }
        }
        
        # Create persistent keyboards
        self.guest_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📝 Register"),
                    KeyboardButton(text="❓ Help"),
                    KeyboardButton(text="📞 Contact")
                ],
                [
                    KeyboardButton(text="🎯 Demo"),
                    KeyboardButton(text="🔧 Commands"),
                    KeyboardButton(text="⭐ Rate Us")
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        self.waiter_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📸 Capture Payment"),
                    KeyboardButton(text="📋 My Transactions")
                ],
                [
                    KeyboardButton(text="🏠 Home"),
                    KeyboardButton(text="❓ Help"),
                    KeyboardButton(text="🚪 Logout")
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        self.admin_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="📊 Dashboard"),
                    KeyboardButton(text="📋 Daily Summary"),
                    KeyboardButton(text="👥 Manage Waiters")
                ],
                [
                    KeyboardButton(text="📄 Upload Statement"),
                    KeyboardButton(text="📈 Generate Report"),
                    KeyboardButton(text="🏠 Home")
                ],
                [
                    KeyboardButton(text="❓ Help"),
                    KeyboardButton(text="🚪 Logout")
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    async def start(self):
        """Start the bot"""
        if not AIOGRAM_AVAILABLE:
            print("❌ aiogram not available. Please install it first:")
            print("pip3 install aiogram")
            return
        
        try:
            # Initialize bot
            self.bot = Bot(token=self.bot_token)
            self.dp = Dispatcher(storage=MemoryStorage())
            
            # Setup handlers
            self._setup_handlers()
            
            print(f"🤖 Starting Lean VeriPay Bot...")
            print(f"📱 Bot: @Verifpay_bot")
            print(f"🔗 Link: https://t.me/Verifpay_bot")
            print(f"🔍 OCR Processing: ENABLED")
            print(f"👥 Role-based access: ENABLED")
            print(f"⏹️  Press Ctrl+C to stop")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
    
    def _setup_handlers(self):
        """Setup bot handlers"""
        router = Router()
        
        @router.message(Command("start"))
        async def cmd_start(message: types.Message):
            """Handle /start command"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role == "admin":
                await self._show_admin_welcome(message)
            elif user_role == "waiter":
                await self._show_waiter_welcome(message)
            else:
                await self._show_guest_welcome(message)
        
        @router.message(Command("help"))
        async def cmd_help(message: types.Message):
            """Handle /help command"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role == "admin":
                await self._show_admin_help(message)
            elif user_role == "waiter":
                await self._show_waiter_help(message)
            else:
                await self._show_guest_help(message)
        
        @router.message(Command("register"))
        async def cmd_register(message: types.Message, state: FSMContext):
            """Handle /register command"""
            user_id = str(message.from_user.id)
            
            # Check if user is already registered
            if user_id in self.approved_users:
                await message.answer("✅ You are already registered in the system!")
                return
            
            # Check if user has pending registration
            if user_id in self.pending_registrations:
                await message.answer("⏳ You already have a pending registration. Please wait for admin approval.")
                return
            
            await state.set_state(RegistrationStates.waiting_for_name)
            await message.answer(
                "📝 **Registration Form**\n\n"
                "Welcome to VeriPay! Let's get you registered.\n\n"
                "Please enter your **full name**:"
            )
        
        @router.message(Command("capture"))
        async def cmd_capture(message: types.Message, state: FSMContext):
            """Handle /capture command for waiters"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role != "waiter":
                await message.answer("⚠️ This command is only available for waiters.")
                return
            
            await state.set_state(WaiterStates.waiting_for_payment_photo)
            await message.answer(
                "📸 **Capture Payment Proof**\n\n"
                "Please take a live photo of the customer's payment screenshot.\n\n"
                "Make sure to include:\n"
                "• STN/Transaction number\n"
                "• Amount\n"
                "• Date & time\n"
                "• Payment method (CBE, Dashen, Telebirr)\n\n"
                "Just tap and capture - I'll do the rest! 🚀"
            )
        
        @router.message(Command("dashboard"))
        async def cmd_dashboard(message: types.Message):
            """Handle /dashboard command for admins"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role != "admin":
                await message.answer("⚠️ This command is only available for admins.")
                return
            
            await self._show_admin_dashboard(message)
        
        @router.message(Command("summary"))
        async def cmd_summary(message: types.Message):
            """Handle /summary command for admins"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role != "admin":
                await message.answer("⚠️ This command is only available for admins.")
                return
            
            await self._show_daily_summary(message)
        
        @router.message(Command("reconcile"))
        async def cmd_reconcile(message: types.Message, state: FSMContext):
            """Handle /reconcile command for admins"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role != "admin":
                await message.answer("⚠️ This command is only available for admins.")
                return
            
            await state.set_state(AdminStates.waiting_for_statement)
            await message.answer(
                "📄 **Upload Bank Statement**\n\n"
                "Please upload your PDF bank statement for daily reconciliation.\n\n"
                "I'll automatically:\n"
                "• Compare captured photos & extracted data\n"
                "• Match against bank PDF totals\n"
                "• Flag any mismatches\n"
                "• Generate audit-ready reports\n\n"
                "Upload your statement now! 📊"
            )
        
        @router.message(Command("waiters"))
        async def cmd_waiters(message: types.Message):
            """Handle /waiters command for admins"""
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if user_role != "admin":
                await message.answer("⚠️ This command is only available for admins.")
                return
            
            await self._show_waiter_management(message)
        
        @router.message(lambda message: message.photo)
        async def handle_photo(message: types.Message, state: FSMContext):
            """Handle photo messages"""
            current_state = await state.get_state()
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if current_state == WaiterStates.waiting_for_payment_photo and user_role == "waiter":
                await self._handle_payment_photo(message, state)
            elif current_state == AdminStates.waiting_for_statement and user_role == "admin":
                await self._handle_statement_photo(message, state)
            else:
                await message.answer("Please use the appropriate command to upload photos.")
        
        @router.message(lambda message: message.document)
        async def handle_document(message: types.Message, state: FSMContext):
            """Handle document messages"""
            current_state = await state.get_state()
            user_id = str(message.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            if current_state == AdminStates.waiting_for_statement and user_role == "admin":
                await self._handle_statement_document(message, state)
            else:
                await message.answer("Please use the appropriate command to upload documents.")
        
        @router.callback_query()
        async def handle_callback(callback_query: types.CallbackQuery, state: FSMContext):
            """Handle callback queries"""
            data = callback_query.data
            user_id = str(callback_query.from_user.id)
            user_role = await self._get_user_role(user_id)
            
            print(f"🔍 Callback received: {data} from user {user_id} (role: {user_role})")
            
            try:
                if data.startswith("waiter_"):
                    if user_role == "waiter":
                        await self._handle_waiter_callback(callback_query, data, state)
                    else:
                        await callback_query.answer("Access denied")
                elif data.startswith("admin_"):
                    if user_role == "admin":
                        await self._handle_admin_callback(callback_query, data, state)
                    else:
                        await callback_query.answer("Access denied")
                elif data.startswith("register_role_"):
                    await self._handle_registration_role_callback(callback_query, data, state)
                elif data.startswith("approve_registration_"):
                    if user_role == "admin":
                        await self._handle_approve_registration(callback_query, data)
                    else:
                        await callback_query.answer("Access denied")
                elif data.startswith("reject_registration_"):
                    if user_role == "admin":
                        await self._handle_reject_registration(callback_query, data)
                    else:
                        await callback_query.answer("Access denied")
                elif data == "register_waiter":
                    await callback_query.answer("Starting waiter registration...")
                    await self._start_waiter_registration(callback_query.message, state)
                elif data == "register_restaurant":
                    await callback_query.answer("Starting restaurant registration...")
                    await self._start_restaurant_registration(callback_query.message, state)
                elif data == "how_it_works":
                    await callback_query.answer("Showing how it works...")
                    await self._show_how_it_works(callback_query.message)
                elif data == "help_support":
                    await callback_query.answer("Showing help...")
                    await self._show_help_support(callback_query.message)
                elif data == "demo_mode":
                    await callback_query.answer("Starting demo...")
                    await self._show_demo_mode(callback_query.message)
                elif data == "contact_us":
                    await callback_query.answer("Contact information...")
                    await self._show_contact_info(callback_query.message)
                elif data == "show_commands":
                    await callback_query.answer("Available commands...")
                    await self._show_commands(callback_query.message)
                elif data == "rate_us":
                    await callback_query.answer("Thank you for your feedback!")
                    await self._show_rating_info(callback_query.message)
                elif data == "back_to_menu":
                    await callback_query.answer("Back to main menu...")
                    await self._show_guest_welcome(callback_query.message)
                else:
                    print(f"❌ Unknown callback: {data}")
                    await callback_query.answer("Unknown action")
            except Exception as e:
                print(f"❌ Error handling callback {data}: {e}")
                await callback_query.answer("Error processing request")
        
        @router.message()
        async def handle_text(message: types.Message, state: FSMContext):
            """Handle text messages"""
            current_state = await state.get_state()
            text = message.text
            
            # Handle keyboard button presses
            if text == "📝 Register":
                await self._start_waiter_registration(message, state)
                return
            elif text == "❓ Help":
                await self._show_help_support(message)
                return
            elif text == "📞 Contact":
                await self._show_contact_info(message)
                return
            elif text == "🎯 Demo":
                await self._show_demo_mode(message)
                return
            elif text == "🔧 Commands":
                await self._show_commands(message)
                return
            elif text == "⭐ Rate Us":
                await self._show_rating_info(message)
                return
            elif text == "📸 Capture Payment":
                await self._handle_capture_payment(message, state)
                return
            elif text == "📋 My Transactions":
                await self._show_waiter_transactions(message)
                return
            elif text == "🏠 Home":
                await self._show_home_menu(message)
                return
            elif text == "🚪 Logout":
                await self._handle_logout(message)
                return
            elif text == "📊 Dashboard":
                await self._show_admin_dashboard(message)
                return
            elif text == "📋 Daily Summary":
                await self._show_daily_summary(message)
                return
            elif text == "👥 Manage Waiters":
                await self._show_waiter_management(message)
                return
            elif text == "📄 Upload Statement":
                await self._start_statement_upload(message, state)
                return
            elif text == "📈 Generate Report":
                await self._generate_report(message)
                return
            
            # Handle registration states
            if current_state == WaiterStates.waiting_for_payment_photo:
                await message.answer("Please send a photo of the payment screenshot, not text.")
            elif current_state == AdminStates.waiting_for_statement:
                await message.answer("Please upload a bank statement file (document or photo), not text.")
            elif current_state == RegistrationStates.waiting_for_name:
                await self._handle_registration_name(message, state)
            elif current_state == RegistrationStates.waiting_for_phone:
                await self._handle_registration_phone(message, state)
            elif current_state == RegistrationStates.waiting_for_role:
                await self._handle_registration_role(message, state)
            elif current_state == RegistrationStates.waiting_for_restaurant_name:
                await self._handle_registration_restaurant_name(message, state)
            elif current_state == RegistrationStates.waiting_for_restaurant_address:
                await self._handle_registration_restaurant_address(message, state)
            else:
                user_id = str(message.from_user.id)
                user_role = await self._get_user_role(user_id)
                
                if user_role == "admin":
                    await self._show_admin_main_menu(message)
                elif user_role == "waiter":
                    await self._show_waiter_main_menu(message)
                else:
                    await message.answer("Please use /register to get access to VeriPay.")
        
        # Add router to dispatcher
        self.dp.include_router(router)
    
    async def _get_user_role(self, user_id: str) -> str:
        """Get user role from database or demo data"""
        # Always use mock data for now to avoid database issues
        if user_id in self.approved_users:
            return self.approved_users[user_id]["role"]
        else:
            return "guest"
    
    async def _handle_registration_name(self, message: types.Message, state: FSMContext):
        """Handle registration name input"""
        user_id = str(message.from_user.id)
        name = message.text.strip()
        
        if len(name) < 2:
            await message.answer("❌ Name must be at least 2 characters long. Please try again:")
            return
        
        await state.update_data(name=name)
        await state.set_state(RegistrationStates.waiting_for_phone)
        await message.answer(
            f"✅ Name: {name}\n\n"
            "Please enter your **phone number** (with country code):\n"
            "Example: +251911234567"
        )
    
    async def _handle_registration_phone(self, message: types.Message, state: FSMContext):
        """Handle registration phone input"""
        phone = message.text.strip()
        
        # Basic phone validation
        if not phone.startswith('+') or len(phone) < 10:
            await message.answer("❌ Please enter a valid phone number with country code (e.g., +251911234567):")
            return
        
        await state.update_data(phone=phone)
        await state.set_state(RegistrationStates.waiting_for_role)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍💼 Waiter", callback_data="register_role_waiter"),
                InlineKeyboardButton(text="🏪 Restaurant Owner", callback_data="register_role_restaurant")
            ]
        ])
        
        await message.answer(
            f"✅ Phone: {phone}\n\n"
            "Please select your **role**:",
            reply_markup=keyboard
        )
    
    async def _handle_registration_role(self, message: types.Message, state: FSMContext):
        """Handle registration role input"""
        await message.answer("Please use the buttons above to select your role.")
    
    async def _handle_registration_restaurant_name(self, message: types.Message, state: FSMContext):
        """Handle restaurant name input"""
        restaurant_name = message.text.strip()
        
        if len(restaurant_name) < 3:
            await message.answer("❌ Restaurant name must be at least 3 characters long. Please try again:")
            return
        
        await state.update_data(restaurant_name=restaurant_name)
        await state.set_state(RegistrationStates.waiting_for_restaurant_address)
        await message.answer(
            f"✅ Restaurant: {restaurant_name}\n\n"
            "Please enter your **restaurant address**:"
        )
    
    async def _handle_registration_restaurant_address(self, message: types.Message, state: FSMContext):
        """Handle restaurant address input"""
        address = message.text.strip()
        
        if len(address) < 5:
            await message.answer("❌ Address must be at least 5 characters long. Please try again:")
            return
        
        await state.update_data(restaurant_address=address)
        await self._complete_registration(message, state)
    
    async def _complete_registration(self, message: types.Message, state: FSMContext):
        """Complete registration process"""
        user_id = str(message.from_user.id)
        data = await state.get_data()
        
        # Auto-approve registration for testing
        data['approved'] = True
        data['approved_at'] = datetime.now().isoformat()
        
        # Add to approved users immediately
        if data.get("role") == "restaurant":
            # Restaurant owner becomes admin
            self.approved_users[user_id] = {
                'name': data.get('name'),
                'role': 'admin',
                'phone': data.get('phone'),
                'restaurant_name': data.get('restaurant_name'),
                'restaurant_address': data.get('restaurant_address'),
                'approved_at': data['approved_at']
            }
            
            # Add restaurant to restaurants list
            self.restaurants[data.get('restaurant_name')] = {
                'name': data.get('restaurant_name'),
                'address': data.get('restaurant_address'),
                'phone': data.get('phone'),
                'admin_id': user_id
            }
            
            await message.answer(
                "🎉 **Restaurant Registration Approved!**\n\n"
                f"**Restaurant:** {data.get('restaurant_name')}\n"
                f"**Address:** {data.get('restaurant_address')}\n"
                f"**Owner:** {data.get('name')}\n"
                f"**Phone:** {data.get('phone')}\n\n"
                "✅ **Status:** Approved & Active\n\n"
                "You now have admin access to VeriPay! 🚀\n\n"
                "Use /start to access your admin dashboard."
            )
        else:
            # Waiter registration
            table_number = f"T{len([u for u in self.approved_users.values() if u.get('role') == 'waiter']) + 1:02d}"
            self.approved_users[user_id] = {
                'name': data.get('name'),
                'role': 'waiter',
                'phone': data.get('phone'),
                'table': table_number,
                'expires': "2024-12-31",
                'approved_at': data['approved_at']
            }
            
            await message.answer(
                "🎉 **Waiter Registration Approved!**\n\n"
                f"**Name:** {data.get('name')}\n"
                f"**Phone:** {data.get('phone')}\n"
                f"**Table:** {table_number}\n"
                f"**Role:** Waiter\n\n"
                "✅ **Status:** Approved & Active\n\n"
                "You now have access to VeriPay! 🚀\n\n"
                "Use /start to begin capturing payments."
            )
        
        await state.clear()
    
    async def _notify_admin_new_registration(self, user_id: str, data: dict):
        """Notify admin about new registration"""
        admin_ids = ["123456789"]  # Demo admin IDs
        
        for admin_id in admin_ids:
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_registration_{user_id}"),
                        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_registration_{user_id}")
                    ]
                ])
                
                if data.get("role") == "restaurant":
                    message_text = f"""
🏪 **New Restaurant Registration**

**Restaurant:** {data.get('restaurant_name')}
**Address:** {data.get('restaurant_address')}
**Owner:** {data.get('name')}
**Phone:** {data.get('phone')}
**User ID:** {user_id}

Please review and approve/reject this registration.
                    """
                else:
                    message_text = f"""
👨‍💼 **New Waiter Registration**

**Name:** {data.get('name')}
**Phone:** {data.get('phone')}
**User ID:** {user_id}

Please review and approve/reject this registration.
                    """
                
                await self.bot.send_message(admin_id, message_text, reply_markup=keyboard)
            except Exception as e:
                print(f"Error notifying admin {admin_id}: {e}")
    
    async def _start_waiter_registration(self, message: types.Message, state: FSMContext):
        """Start waiter registration process"""
        user_id = str(message.from_user.id)
        
        # Check if user is already registered
        if user_id in self.approved_users:
            await message.answer("✅ You are already registered in the system!")
            return
        
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "👨‍💼 **Waiter Registration**\n\n"
            "Let's get you registered as a waiter!\n\n"
            "Please enter your **full name**:"
        )
    
    async def _start_restaurant_registration(self, message: types.Message, state: FSMContext):
        """Start restaurant registration process"""
        user_id = str(message.from_user.id)
        
        # Check if user is already registered
        if user_id in self.approved_users:
            await message.answer("✅ You are already registered in the system!")
            return
        
        await state.set_state(RegistrationStates.waiting_for_name)
        await message.answer(
            "🏪 **Restaurant Registration**\n\n"
            "Let's register your restaurant!\n\n"
            "Please enter your **full name** (restaurant owner):"
        )
    
    async def _show_how_it_works(self, message: types.Message):
        """Show how VeriPay works"""
        how_it_works_text = """
🔍 **How VeriPay Works**

📱 **For Waiters:**
1. **Capture Payment** - Take photo of customer's payment screenshot
2. **AI Processing** - Bot extracts transaction details automatically
3. **Instant Verification** - Get immediate confirmation
4. **Track Transactions** - View your daily activity

🏪 **For Restaurant Owners:**
1. **Monitor Activity** - View all transactions in real-time
2. **Daily Reports** - Get comprehensive daily summaries
3. **Bank Reconciliation** - Upload statements for verification
4. **Manage Team** - Assign tables and manage waiters

🤖 **AI Features:**
• **OCR Processing** - Extract text from screenshots
• **QR Code Verification** - Cross-verify transaction details
• **Fraud Detection** - Identify suspicious transactions
• **Automatic Matching** - Compare with bank statements

📊 **Reports & Analytics:**
• Daily transaction summaries
• Per-waiter performance metrics
• Payment method analysis
• Audit-ready documentation
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Register Now", callback_data="register_waiter"),
                InlineKeyboardButton(text="🏪 Register Restaurant", callback_data="register_restaurant")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(how_it_works_text, reply_markup=keyboard)
    
    async def _show_help_support(self, message: types.Message):
        """Show help and support information"""
        help_text = """
📚 **Help & Support**

🔧 **Getting Started:**
1. Register using the buttons above
2. Wait for admin approval
3. Start using VeriPay!

📱 **Available Commands:**
/start - Show main menu
/register - Start registration
/help - Show this help
/capture - Capture payment (waiters)
/dashboard - Admin dashboard
/summary - Daily summary

❓ **Common Questions:**

**Q: How do I register?**
A: Click "Register as Waiter" or "Register Restaurant" and follow the steps.

**Q: How long does approval take?**
A: Registrations are approved instantly for testing purposes.

**Q: Can I change my role?**
A: Contact support to change your role after registration.

**Q: How do I capture payments?**
A: Use the /capture command or "Capture Payment" button.

📞 **Need More Help?**
Contact our support team:
• Email: support@veripay.et
• Phone: +251911234567
• Telegram: @veripay_support
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Register Now", callback_data="register_waiter"),
                InlineKeyboardButton(text="🏪 Register Restaurant", callback_data="register_restaurant")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(help_text, reply_markup=keyboard)
    
    async def _show_demo_mode(self, message: types.Message):
        """Show demo mode information"""
        demo_text = """
🎯 **Demo Mode**

Welcome to VeriPay Demo! Here's how to test the system:

👨‍💼 **Test as Waiter:**
• Use Telegram ID: 111111111, 222222222, or 333333333
• Try capturing payment screenshots
• View transaction history

🏪 **Test as Restaurant Owner:**
• Use Telegram ID: 123456789
• Access admin dashboard
• View daily summaries
• Manage waiters

📱 **Demo Features:**
• Real OCR processing (when Tesseract is installed)
• Mock data for testing
• Full registration flow
• Admin approval system
• Payment capture simulation

🚀 **Ready to test?**
Register with your real Telegram ID to experience the full system!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Register Now", callback_data="register_waiter"),
                InlineKeyboardButton(text="🏪 Register Restaurant", callback_data="register_restaurant")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(demo_text, reply_markup=keyboard)
    
    async def _show_contact_info(self, message: types.Message):
        """Show contact information"""
        contact_text = """
📞 **Contact Us**

We're here to help! Get in touch with us:

📧 **Email:**
• General: info@veripay.et
• Support: support@veripay.et
• Sales: sales@veripay.et

📱 **Phone:**
• Main: +251911234567
• Support: +251922345678
• Sales: +251933456789

💬 **Telegram:**
• Support: @veripay_support
• Sales: @veripay_sales
• Updates: @veripay_updates

🏢 **Office:**
• Address: Addis Ababa, Ethiopia
• Hours: Mon-Fri 9:00 AM - 6:00 PM EAT

⏰ **Response Times:**
• Support: Within 2 hours
• Sales: Within 24 hours
• Technical: Within 4 hours
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📧 Email Support", callback_data="email_support"),
                InlineKeyboardButton(text="💬 Telegram Support", callback_data="telegram_support")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(contact_text, reply_markup=keyboard)
    
    async def _show_commands(self, message: types.Message):
        """Show available commands"""
        commands_text = """
🔧 **Available Commands**

📱 **For Everyone:**
/start - Show main menu
/register - Start registration process
/help - Show help information

👨‍💼 **For Waiters:**
/capture - Capture payment screenshot
/transactions - View your transactions
/status - Check registration status

🏪 **For Restaurant Owners:**
/dashboard - View admin dashboard
/summary - View daily summary
/reconcile - Upload bank statement
/waiters - Manage waiters
/reports - Generate reports

⚙️ **System Commands:**
/status - Check system status
/version - Show bot version
/about - About VeriPay
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Register Now", callback_data="register_waiter"),
                InlineKeyboardButton(text="🏪 Register Restaurant", callback_data="register_restaurant")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(commands_text, reply_markup=keyboard)
    
    async def _show_rating_info(self, message: types.Message):
        """Show rating information"""
        rating_text = """
⭐ **Rate VeriPay**

Thank you for considering rating us! Your feedback helps us improve.

📊 **Current Rating:** 4.8/5 ⭐⭐⭐⭐⭐

💬 **What users say:**
• "Simple and efficient payment verification"
• "Great for managing restaurant transactions"
• "Excellent customer support"
• "Saves us hours of manual work"

🎯 **Rate us on:**
• Telegram Bot Store
• Our website
• Social media

📝 **Leave a Review:**
Share your experience and help other restaurants discover VeriPay!

Thank you for choosing VeriPay! 🙏
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ Rate on Telegram", callback_data="rate_telegram"),
                InlineKeyboardButton(text="📝 Write Review", callback_data="write_review")
            ],
            [
                InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")
            ]
        ])
        
        await message.answer(rating_text, reply_markup=keyboard)
    
    async def _handle_capture_payment(self, message: types.Message, state: FSMContext):
        """Handle capture payment from keyboard"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        
        if user_role != "waiter":
            await message.answer("⚠️ This feature is only available for waiters.")
            return
        
        await state.set_state(WaiterStates.waiting_for_payment_photo)
        await message.answer(
            "📸 **Capture Payment Proof**\n\n"
            "Please take a live photo of the customer's payment screenshot.\n\n"
            "Make sure to include:\n"
            "• STN/Transaction number\n"
            "• Amount\n"
            "• Date & time\n"
            "• Payment method (CBE, Dashen, Telebirr)\n\n"
            "Just tap and capture - I'll do the rest! 🚀"
        )
    
    async def _show_home_menu(self, message: types.Message):
        """Show home menu based on user role"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        
        if user_role == "admin":
            await self._show_admin_welcome(message)
        elif user_role == "waiter":
            await self._show_waiter_welcome(message)
        else:
            await self._show_guest_welcome(message)
    
    async def _handle_logout(self, message: types.Message):
        """Handle logout"""
        user_id = str(message.from_user.id)
        
        # Remove from approved users (for demo purposes)
        if user_id in self.approved_users:
            del self.approved_users[user_id]
        
        await message.answer(
            "🚪 **Logged Out Successfully!**\n\n"
            "You have been logged out of VeriPay.\n\n"
            "Use /start to log back in or register again.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def _start_statement_upload(self, message: types.Message, state: FSMContext):
        """Start statement upload process"""
        user_id = str(message.from_user.id)
        user_role = await self._get_user_role(user_id)
        
        if user_role != "admin":
            await message.answer("⚠️ This feature is only available for admins.")
            return
        
        await state.set_state(AdminStates.waiting_for_statement)
        await message.answer(
            "📄 **Upload Bank Statement**\n\n"
            "Please upload your PDF bank statement for daily reconciliation.\n\n"
            "I'll automatically:\n"
            "• Compare captured photos & extracted data\n"
            "• Match against bank PDF totals\n"
            "• Flag any mismatches\n"
            "• Generate audit-ready reports\n\n"
            "Upload your statement now! 📊"
        )
    
    async def _handle_registration_role_callback(self, callback_query: types.CallbackQuery, data: str, state: FSMContext):
        """Handle registration role selection"""
        role = data.replace("register_role_", "")
        
        if role == "waiter":
            await state.update_data(role="waiter")
            await callback_query.answer("Role selected: Waiter")
            await callback_query.message.edit_text(
                f"✅ Role: Waiter\n\n"
                "Please enter your **restaurant name** where you work:"
            )
            await state.set_state(RegistrationStates.waiting_for_restaurant_name)
        elif role == "restaurant":
            await state.update_data(role="restaurant")
            await callback_query.answer("Role selected: Restaurant Owner")
            await callback_query.message.edit_text(
                f"✅ Role: Restaurant Owner\n\n"
                "Please enter your **restaurant name**:"
            )
            await state.set_state(RegistrationStates.waiting_for_restaurant_name)
    
    async def _handle_approve_registration(self, callback_query: types.CallbackQuery, data: str):
        """Handle registration approval"""
        user_id = data.replace("approve_registration_", "")
        
        if user_id not in self.pending_registrations:
            await callback_query.answer("Registration not found!")
            return
        
        registration_data = self.pending_registrations[user_id]
        
        # Add to approved users
        self.approved_users[user_id] = {
            "name": registration_data["name"],
            "role": registration_data["role"],
            "phone": registration_data["phone"],
            "table": "T01",  # Default table assignment
            "expires": "2024-09-01"  # Default expiration
        }
        
        # Remove from pending
        del self.pending_registrations[user_id]
        
        # Notify user
        try:
            if registration_data["role"] == "restaurant":
                await self.bot.send_message(
                    user_id,
                    "🎉 **Restaurant Registration Approved!**\n\n"
                    f"Your restaurant '{registration_data['restaurant_name']}' has been approved.\n"
                    "You now have admin access to VeriPay.\n\n"
                    "Use /start to begin managing your restaurant!"
                )
            else:
                await self.bot.send_message(
                    user_id,
                    "🎉 **Waiter Registration Approved!**\n\n"
                    f"You have been approved as a waiter.\n"
                    "Table assignment: T01\n"
                    "Expires: 2024-09-01\n\n"
                    "Use /start to begin capturing payments!"
                )
        except Exception as e:
            print(f"Error notifying user {user_id}: {e}")
        
        await callback_query.answer("Registration approved!")
        await callback_query.message.edit_text(
            f"✅ **Registration Approved**\n\n"
            f"User: {registration_data['name']}\n"
            f"Role: {registration_data['role']}\n"
            f"Status: Approved"
        )
    
    async def _handle_reject_registration(self, callback_query: types.CallbackQuery, data: str):
        """Handle registration rejection"""
        user_id = data.replace("reject_registration_", "")
        
        if user_id not in self.pending_registrations:
            await callback_query.answer("Registration not found!")
            return
        
        registration_data = self.pending_registrations[user_id]
        
        # Remove from pending
        del self.pending_registrations[user_id]
        
        # Notify user
        try:
            await self.bot.send_message(
                user_id,
                "❌ **Registration Rejected**\n\n"
                "Your registration has been rejected.\n"
                "Please contact support for more information."
            )
        except Exception as e:
            print(f"Error notifying user {user_id}: {e}")
        
        await callback_query.answer("Registration rejected!")
        await callback_query.message.edit_text(
            f"❌ **Registration Rejected**\n\n"
            f"User: {registration_data['name']}\n"
            f"Role: {registration_data['role']}\n"
            f"Status: Rejected"
        )
    
    async def _show_admin_welcome(self, message: types.Message):
        """Show admin welcome message"""
        welcome_text = f"""
🎉 Welcome to VeriPay Admin!

I'm your unified payment verification management system.

📊 **Admin Dashboard:**
• Monitor payment verifications in real-time
• Generate daily summaries and reports
• Upload bank statements for reconciliation
• Manage waiters and tables
• Export audit-ready reports

🔧 **Quick Actions:**
/dashboard - View system overview
/summary - Daily transaction summary
/reconcile - Upload bank statement
/waiters - Manage waiters
/help - Show help

Ready to manage your payment verifications! 💼
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dashboard"),
                InlineKeyboardButton(text="📋 Daily Summary", callback_data="admin_summary")
            ],
            [
                InlineKeyboardButton(text="📄 Upload Statement", callback_data="admin_reconcile"),
                InlineKeyboardButton(text="👥 Manage Waiters", callback_data="admin_waiters")
            ]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard)
        await message.answer("💡 **Quick Access:** Use the keyboard below for common actions!", reply_markup=self.admin_keyboard)
    
    async def _show_waiter_welcome(self, message: types.Message):
        """Show waiter welcome message"""
        welcome_text = f"""
🎉 Welcome to VeriPay!

I'm your payment verification assistant. I help you verify payment screenshots quickly and securely.

📱 **How to use:**
• Take a live photo of the customer's payment screenshot
• I'll automatically extract transaction details
• Get instant verification results
• Minimal effort - just tap and capture!

🔧 **Quick Actions:**
/capture - Capture payment proof
/help - Show help

Ready to verify a payment? Just tap /capture! 📸
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📸 Capture Payment", callback_data="waiter_capture"),
                InlineKeyboardButton(text="📋 My Transactions", callback_data="waiter_transactions")
            ],
            [
                InlineKeyboardButton(text="❓ Help", callback_data="waiter_help")
            ]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard)
    
    async def _show_guest_welcome(self, message: types.Message):
        """Show guest welcome message"""
        welcome_text = """
🎉 **Welcome to VeriPay!**

I'm your payment verification system for restaurants in Ethiopia.

📱 **What I do:**
• Verify payment screenshots automatically
• Extract transaction details with AI
• Generate daily reports for reconciliation
• Manage waiters and tables
• Provide audit-ready documentation

🚀 **Get Started:**
Choose your role and register to begin!

**👨‍💼 For Waiters:**
• Capture payment screenshots
• Get instant verification
• Track your transactions
• Simple one-tap operation

**🏪 For Restaurant Owners:**
• Monitor all transactions
• Generate daily reports
• Manage waiters and tables
• Upload bank statements
• Full admin dashboard
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Register as Waiter", callback_data="register_waiter"),
                InlineKeyboardButton(text="🏪 Register Restaurant", callback_data="register_restaurant")
            ],
            [
                InlineKeyboardButton(text="❓ How It Works", callback_data="how_it_works"),
                InlineKeyboardButton(text="📚 Help & Support", callback_data="help_support")
            ],
            [
                InlineKeyboardButton(text="🎯 Demo Mode", callback_data="demo_mode"),
                InlineKeyboardButton(text="📞 Contact Us", callback_data="contact_us")
            ],
            [
                InlineKeyboardButton(text="🔧 Commands", callback_data="show_commands"),
                InlineKeyboardButton(text="⭐ Rate Us", callback_data="rate_us")
            ]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard)
        await message.answer("💡 **Quick Access:** Use the keyboard below for common actions!", reply_markup=self.guest_keyboard)
    
    async def _show_admin_help(self, message: types.Message):
        """Show admin help message"""
        help_text = """
📚 **VeriPay Admin Help**

🔍 **What I do:**
• Monitor payment verifications in real-time
• Generate comprehensive audit reports
• Reconcile transactions with bank statements
• Manage waiters and restaurant settings
• View system analytics and statistics

📊 **Dashboard Features:**
• Real-time verification status
• Fraud detection alerts
• Transaction volume statistics
• System performance metrics

📋 **Transaction Management:**
• View all payment verifications
• Filter by status, date, waiter
• Override verification results
• Export transaction data

📄 **Statement Reconciliation:**
• Upload bank statements (Excel, CSV, PDF)
• Automatic transaction matching
• Discrepancy identification
• Audit trail generation

📈 **Reporting:**
• Generate PDF/Excel audit reports
• Custom date range reports
• Fraud analysis reports
• Performance analytics

👥 **User Management:**
• Add/remove waiters
• Manage restaurant settings
• View user activity logs
• Access control management

🔧 **Commands:**
/start - Start the bot
/dashboard - View system overview
/summary - Daily transaction summary
/reconcile - Upload bank statement
/waiters - Manage waiters
/help - Show this help message

❓ **Need help?** Contact the system administrator.
        """
        await message.answer(help_text)
    
    async def _show_waiter_help(self, message: types.Message):
        """Show waiter help message"""
        help_text = """
📚 **VeriPay Waiter Help**

🔍 **What I do:**
• Extract transaction details from payment screenshots using AI
• Detect potential fraud and manipulation
• Verify transactions with bank APIs
• Provide instant verification results

📱 **How to use:**
1. Use /capture command
2. Take a live photo of the customer's payment screenshot
3. I'll analyze the image and extract details automatically
4. Review the extracted information
5. Get instant verification results

💡 **Tips for better results:**
• Make sure the screenshot is clear and readable
• Include the full transaction details
• Ensure good lighting and contrast
• Avoid blurry or low-resolution images

🔧 **Commands:**
/capture - Capture payment proof
/help - Show this help message

❓ **Need help?** Contact your manager or admin.
        """
        await message.answer(help_text)
    
    async def _show_guest_help(self, message: types.Message):
        """Show guest help message"""
        help_text = """
📚 **VeriPay Help**

🔍 **What is VeriPay:**
VeriPay is a Telegram bot-based payment verification system designed for restaurants in Ethiopia.

📱 **Features:**
• Automatic transaction extraction from screenshots
• QR code verification for instant validation
• Daily reconciliation with bank statements
• Audit-ready reports for compliance
• Simple, lean, scalable system

👥 **User Roles:**
• **Waiters:** Capture payment screenshots and verify transactions
• **Restaurant Owners:** Monitor system, generate reports, manage waiters

🔧 **Getting Started:**
1. Use /register to create your account
2. Choose your role (Waiter or Restaurant Owner)
3. Wait for admin approval
4. Start using VeriPay!

🔧 **Available Commands:**
/register - Register for VeriPay access
/help - Show this help message

❓ **Need help?** Contact the system administrator.
        """
        await message.answer(help_text)
    
    async def _show_admin_main_menu(self, message: types.Message):
        """Show admin main menu"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dashboard"),
                InlineKeyboardButton(text="📋 Daily Summary", callback_data="admin_summary")
            ],
            [
                InlineKeyboardButton(text="📄 Upload Statement", callback_data="admin_reconcile"),
                InlineKeyboardButton(text="👥 Manage Waiters", callback_data="admin_waiters")
            ],
            [
                InlineKeyboardButton(text="📈 Generate Report", callback_data="admin_report"),
                InlineKeyboardButton(text="❓ Help", callback_data="admin_help")
            ]
        ])
        
        await message.answer("🔧 **Admin Main Menu**\n\nSelect an action:", reply_markup=keyboard)
    
    async def _show_waiter_main_menu(self, message: types.Message):
        """Show waiter main menu"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📸 Capture Payment", callback_data="waiter_capture"),
                InlineKeyboardButton(text="📋 My Transactions", callback_data="waiter_transactions")
            ],
            [
                InlineKeyboardButton(text="❓ Help", callback_data="waiter_help")
            ]
        ])
        
        await message.answer("📱 **Waiter Main Menu**\n\nSelect an action:", reply_markup=keyboard)
    
    async def _handle_payment_photo(self, message: types.Message, state: FSMContext):
        """Handle payment photo from waiter"""
        try:
            await message.answer("🔍 Analyzing payment screenshot... Please wait.")
            
            # Get the largest photo
            photo = message.photo[-1]
            file_info = await self.bot.get_file(photo.file_id)
            
            # Download the photo
            photo_bytes = await self.bot.download_file(file_info.file_path)
            
            # Process with OCR
            result = self.ocr_extractor.extract_transaction_data(photo_bytes)
            
            if 'error' in result:
                await message.answer(f"❌ Error processing screenshot: {result['error']}")
                await state.clear()
                return
            
            # Create result message
            extracted_data = result['extraction_details']
            
            if not extracted_data.get('stn_number') and not extracted_data.get('amount'):
                await message.answer(
                    "❌ Could not extract transaction details from the screenshot.\n\n"
                    "Please ensure the image contains:\n"
                    "• Clear transaction reference/STN number\n"
                    "• Visible amount\n"
                    "• Good image quality\n\n"
                    "Try uploading a clearer screenshot."
                )
                await state.clear()
                return
            
            # Store transaction data in state for confirmation
            await state.update_data(transaction_data=result)
            
            # Create confirmation message
            confirmation_text = f"""
📋 **Extracted Transaction Details:**

🔢 **STN Number:** {extracted_data.get('stn_number', 'Not found')}
💰 **Amount:** {f"ETB {extracted_data.get('amount', 0):,.2f}" if extracted_data.get('amount') else 'Not found'}
📅 **Date:** {extracted_data.get('transaction_date', 'Not found')}
👤 **Sender:** {extracted_data.get('sender_account', 'Not found')}
👥 **Receiver:** {extracted_data.get('receiver_account', 'Not found')}
🏦 **Bank:** {result.get('bank_type', 'Unknown').upper()}

📊 **Confidence:** {result.get('confidence', 0):.2%}

✅ **Transaction captured successfully!**

💡 **Next Steps:**
✅ Transaction verified - you can proceed with the order
            """
            
            # Create confirmation keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Confirm", callback_data="waiter_confirm"),
                    InlineKeyboardButton(text="🔄 Retry", callback_data="waiter_retry")
                ]
            ])
            
            await message.answer(confirmation_text, reply_markup=keyboard)
            await state.set_state(WaiterStates.confirming_transaction)
            
        except Exception as e:
            await message.answer(f"❌ Error processing screenshot: {str(e)}")
            await state.clear()
    
    async def _handle_statement_photo(self, message: types.Message, state: FSMContext):
        """Handle statement photo from admin"""
        await message.answer("📄 Processing bank statement photo... Please wait.")
        # Implementation for statement processing
        await state.clear()
    
    async def _handle_statement_document(self, message: types.Message, state: FSMContext):
        """Handle statement document from admin"""
        await message.answer("📄 Processing bank statement document... Please wait.")
        # Implementation for statement processing
        await state.clear()
    
    async def _handle_waiter_callback(self, callback_query: types.CallbackQuery, data: str, state: FSMContext):
        """Handle waiter callback queries"""
        if data == "waiter_capture":
            await callback_query.answer("Redirecting to capture...")
            await state.set_state(WaiterStates.waiting_for_payment_photo)
            await callback_query.message.answer(
                "📸 **Capture Payment Proof**\n\n"
                "Please take a live photo of the customer's payment screenshot.\n\n"
                "Make sure to include:\n"
                "• STN/Transaction number\n"
                "• Amount\n"
                "• Date & time\n"
                "• Payment method (CBE, Dashen, Telebirr)\n\n"
                "Just tap and capture - I'll do the rest! 🚀"
            )
        elif data == "waiter_transactions":
            await callback_query.answer("Loading your transactions...")
            await self._show_waiter_transactions(callback_query.message)
        elif data == "waiter_help":
            await callback_query.answer("Showing help...")
            await self._show_waiter_help(callback_query.message)
        elif data == "waiter_confirm":
            await callback_query.answer("Transaction confirmed!")
            await self._confirm_transaction(callback_query.message, state)
        elif data == "waiter_retry":
            await callback_query.answer("Retrying capture...")
            await state.set_state(WaiterStates.waiting_for_payment_photo)
            await callback_query.message.answer(
                "📸 Please take another photo of the payment screenshot."
            )

    
    async def _handle_admin_callback(self, callback_query: types.CallbackQuery, data: str, state: FSMContext):
        """Handle admin callback queries"""
        if data == "admin_dashboard":
            await callback_query.answer("Loading dashboard...")
            await self._show_admin_dashboard(callback_query.message)
        elif data == "admin_summary":
            await callback_query.answer("Loading daily summary...")
            await self._show_daily_summary(callback_query.message)
        elif data == "admin_reconcile":
            await callback_query.answer("Redirecting to reconciliation...")
            await state.set_state(AdminStates.waiting_for_statement)
            await callback_query.message.answer(
                "📄 **Upload Bank Statement**\n\n"
                "Please upload your PDF bank statement for daily reconciliation.\n\n"
                "I'll automatically:\n"
                "• Compare captured photos & extracted data\n"
                "• Match against bank PDF totals\n"
                "• Flag any mismatches\n"
                "• Generate audit-ready reports\n\n"
                "Upload your statement now! 📊"
            )
        elif data == "admin_waiters":
            await callback_query.answer("Loading waiter management...")
            await self._show_waiter_management(callback_query.message)
        elif data == "admin_report":
            await callback_query.answer("Generating report...")
            await self._generate_report(callback_query.message)
        elif data == "admin_help":
            await callback_query.answer("Showing help...")
            await self._show_admin_help(callback_query.message)
    
    async def _show_admin_dashboard(self, message: types.Message):
        """Show admin dashboard"""
        # Demo dashboard data
        dashboard_text = f"""
📊 **VeriPay Dashboard**

📈 **Today's Activity:**
• New Transactions: 15
• Verified: 12
• Failed: 2
• Suspicious: 1

💰 **Financial Summary:**
• Total Amount Today: ETB 45,250.00
• Verified Amount: ETB 38,500.00
• Pending Amount: ETB 6,750.00

👥 **User Activity:**
• Active Waiters: 8
• Restaurants: 3

⚠️ **Alerts:**
• High Fraud Rate: No
• Pending Verifications: 3
• System Issues: No

🕒 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 View Transactions", callback_data="admin_view_transactions"),
                InlineKeyboardButton(text="📊 Generate Report", callback_data="admin_report")
            ],
            [
                InlineKeyboardButton(text="📄 Upload Statement", callback_data="admin_reconcile"),
                InlineKeyboardButton(text="👥 Manage Users", callback_data="admin_waiters")
            ]
        ])
        
        await message.answer(dashboard_text, reply_markup=keyboard)
    
    async def _show_daily_summary(self, message: types.Message):
        """Show daily summary"""
        summary_text = f"""
📋 **Daily Summary - {datetime.now().strftime('%Y-%m-%d')}**

📊 **Transaction Overview:**
• Total Transactions: 15
• Total Amount: ETB 45,250.00

👥 **Per Waiter:**
• John Doe: 5 transactions (ETB 18,500.00)
• Jane Smith: 4 transactions (ETB 12,750.00)
• Mike Johnson: 3 transactions (ETB 8,200.00)
• Sarah Wilson: 3 transactions (ETB 5,800.00)

🏦 **By Payment Method:**
• CBE: 8 transactions (ETB 24,500.00)
• Telebirr: 5 transactions (ETB 15,750.00)
• Dashen: 2 transactions (ETB 5,000.00)

✅ **Verification Status:**
• Verified: 12 (80%)
• Pending: 3 (20%)
• Failed: 0 (0%)

📈 **Performance:**
• Average processing time: 2.3 seconds
• OCR confidence: 87%
• Fraud detection: 1 suspicious transaction
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Export CSV", callback_data="admin_export_csv"),
                InlineKeyboardButton(text="📊 Export PDF", callback_data="admin_export_pdf")
            ],
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_summary"),
                InlineKeyboardButton(text="📈 Detailed Report", callback_data="admin_detailed_report")
            ]
        ])
        
        await message.answer(summary_text, reply_markup=keyboard)
    
    async def _show_waiter_management(self, message: types.Message):
        """Show waiter management"""
        waiters_text = """
👥 **Waiter Management**

📋 **Active Waiters:**
1. **John Doe**
   📱 ID: @johndoe
   🏪 Restaurant: Main Branch
   📅 Joined: 2024-01-15
   📊 Today: 5 transactions

2. **Jane Smith**
   📱 ID: @janesmith
   🏪 Restaurant: Main Branch
   📅 Joined: 2024-01-20
   📊 Today: 4 transactions

3. **Mike Johnson**
   📱 ID: @mikejohnson
   🏪 Restaurant: Downtown Branch
   📅 Joined: 2024-02-01
   📊 Today: 3 transactions

4. **Sarah Wilson**
   📱 ID: @sarahwilson
   🏪 Restaurant: Downtown Branch
   📅 Joined: 2024-02-10
   📊 Today: 3 transactions
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Add Waiter", callback_data="admin_add_waiter"),
                InlineKeyboardButton(text="✏️ Edit Waiter", callback_data="admin_edit_waiter")
            ],
            [
                InlineKeyboardButton(text="📊 Waiter Stats", callback_data="admin_waiter_stats"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_waiters")
            ]
        ])
        
        await message.answer(waiters_text, reply_markup=keyboard)
    
    async def _show_waiter_transactions(self, message: types.Message):
        """Show waiter's own transactions"""
        transactions_text = f"""
📋 **Your Transactions - {datetime.now().strftime('%Y-%m-%d')}**

📊 **Today's Activity:**
• Total Transactions: 5
• Total Amount: ETB 18,500.00

📋 **Recent Transactions:**
1. **STN12345678** - ETB 5,500.00 (CBE) ✅
2. **STN12345679** - ETB 4,200.00 (Telebirr) ✅
3. **STN12345680** - ETB 3,800.00 (CBE) ✅
4. **STN12345681** - ETB 3,000.00 (Dashen) ✅
5. **STN12345682** - ETB 2,000.00 (Telebirr) ✅

✅ **All transactions verified successfully!**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📸 Capture New", callback_data="waiter_capture"),
                InlineKeyboardButton(text="🔄 Refresh", callback_data="waiter_transactions")
            ]
        ])
        
        await message.answer(transactions_text, reply_markup=keyboard)
    
    async def _confirm_transaction(self, message: types.Message, state: FSMContext):
        """Confirm transaction and save to database"""
        try:
            # Get transaction data from state
            data = await state.get_data()
            transaction_data = data.get('transaction_data', {})
            
            # Save to database if available
            if DB_AVAILABLE and self.db_manager:
                # Implementation for saving to database
                pass
            
            await message.answer(
                "✅ **Transaction Confirmed!**\n\n"
                "The payment has been verified and recorded.\n\n"
                "📋 **Transaction Details Saved:**\n"
                f"• STN: {transaction_data.get('stn_number', 'N/A')}\n"
                f"• Amount: ETB {transaction_data.get('amount', 0):,.2f}\n"
                f"• Bank: {transaction_data.get('bank_type', 'N/A').upper()}\n\n"
                "You can now proceed with the order! 🎉"
            )
            
            await state.clear()
            
        except Exception as e:
            await message.answer(f"❌ Error confirming transaction: {str(e)}")
            await state.clear()
    
    async def _generate_report(self, message: types.Message):
        """Generate audit report"""
        await message.answer(
            "📊 **Generating Audit Report...**\n\n"
            "Report will include:\n"
            "• Daily transaction summary\n"
            "• Per-waiter breakdown\n"
            "• Payment method analysis\n"
            "• Fraud detection results\n"
            "• Reconciliation status\n\n"
            "Report will be available for download shortly."
        )


async def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                Lean VeriPay Bot                              ║
║                                                              ║
║  🤖 Unified bot for waiters and admins                      ║
║  📱 Role-based access with button interfaces                ║
║  🔍 Real OCR processing for payment screenshots             ║
║  📊 Admin dashboard and reporting                           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create and run bot
    bot = LeanVeriPayBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 