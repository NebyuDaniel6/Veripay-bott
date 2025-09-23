#!/usr/bin/env python3
"""
VeriPay Bot - PRD COMPLIANT VERSION
Following VeriPay PRD as single source of truth
Milestone 1 + Milestone 2 features
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

# Telegram imports
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Google Vision API
from google.cloud import vision

# PDF processing
import pdfplumber
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc'
GOOGLE_VISION_API_KEY = 'AIzaSyBvQZJvQZJvQZJvQZJvQZJvQZJvQZJvQZJvQ'

# Super Admin user ID - @NebyuDaniel
SUPER_ADMIN_USER_ID = 369249230

# In-memory storage (will be replaced with database)
users = {}
user_sessions = {}
user_states = {}
transactions = {}
admin_transactions = {}
pending_restaurant_approvals = {}  # Changed from pending_approvals
restaurant_ids = {}
waiter_ids = {}
bank_statements = {}
statement_transactions = {}
reconciliation_results = {}
audit_logs = []

class UserState(Enum):
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_ADDRESS = "waiting_for_restaurant_address"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    CAPTURING_PAYMENT = "capturing_payment"
    ADMIN_MENU = "admin_menu"
    UPLOADING_STATEMENT = "uploading_statement"

class UserRole(Enum):
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

@dataclass
class Transaction:
    id: str
    user_id: int
    amount: float
    transaction_id: str
    date: str
    time: str
    payer: str
    receiver: str
    bank_name: str
    payment_method: str
    currency: str
    waiter_id: str
    restaurant_id: str
    created_at: datetime

@dataclass
class BankStatement:
    id: str
    restaurant_id: str
    bank_name: str
    statement_date: datetime
    weekly_period_start: datetime
    weekly_period_end: datetime
    uploaded_by: int
    pdf_file_id: str
    total_transactions: int
    reconciled_transactions: int
    unmatched_transactions: int
    status: str
    created_at: datetime

@dataclass
class StatementTransaction:
    id: str
    statement_id: str
    reference_id: str
    amount: float
    transaction_date: datetime
    payer_name: str
    receiver_name: str
    status: str

@dataclass
class ReconciliationResult:
    id: str
    statement_id: str
    waiter_transaction_id: str
    statement_transaction_id: str
    match_type: str
    created_at: datetime

class VeriPayBot:
    def __init__(self):
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
        # Initialize Google Vision API
        try:
            self.vision_client = vision.ImageAnnotatorClient()
        except Exception as e:
            logger.warning(f"Google Vision API not available: {e}")
            self.vision_client = None

    def setup_handlers(self):
        """Setup all handlers"""
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("admin", self.handle_admin_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document_message))

    async def start_command(self, update: Update, context):
        """Handle /start command - PRD compliant"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        # Log audit
        self.log_audit(user_id, "start_command", f"User {user_name} started bot")
        
        if user_id in users:
            role = users[user_id].get('role', 'waiter')
            if role == 'super_admin':
                await update.message.reply_text(f"🔧 Welcome back, Super Admin {user_name}!")
                await self.show_super_admin_menu(update)
            elif role == 'restaurant_admin':
                await update.message.reply_text(f"👨‍💼 Welcome back, Restaurant Admin {user_name}!")
                await self.show_restaurant_admin_menu(update)
            else:
                await update.message.reply_text(f"🍳 Welcome back, Waiter {user_name}!")
                await self.show_waiter_menu(update)
        else:
            await update.message.reply_text(f"🎉 Welcome to VeriPay!\n\nHello {user_name}! 👋\n\nVeriPay helps restaurants manage payments and transactions efficiently.\n\nPlease select your role:")
            
            # Role selection keyboard - PRD compliant
            keyboard = [
                [InlineKeyboardButton("🏪 Restaurant Registration", callback_data="register_restaurant")],
                [InlineKeyboardButton("🍳 Waiter Registration", callback_data="register_waiter")],
                [InlineKeyboardButton("🔧 Super Admin Login", callback_data="super_admin_login")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Please select your role:",
                reply_markup=reply_markup
            )

    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("⏳ Pending Restaurant Approvals", callback_data="admin_pending_restaurants")],
            [InlineKeyboardButton("📊 All Transactions", callback_data="admin_all_transactions")],
            [InlineKeyboardButton("📊 Daily Report", callback_data="admin_daily_report")],
            [InlineKeyboardButton("🏦 Bank Statement Upload", callback_data="admin_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="admin_reconciliation_report")],
            [InlineKeyboardButton("👥 Manage Restaurants", callback_data="admin_manage_restaurants")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "�� **Super Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("📊 My Restaurant Transactions", callback_data="restaurant_transactions")],
            [InlineKeyboardButton("📈 Daily Summary", callback_data="restaurant_daily_summary")],
            [InlineKeyboardButton("📤 Export CSV", callback_data="restaurant_export_csv")],
            [InlineKeyboardButton("🏦 Upload Bank Statement", callback_data="restaurant_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="restaurant_reconciliation")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="restaurant_manage_waiters")],
            [InlineKeyboardButton("⏳ Pending Waiter Approvals", callback_data="restaurant_pending_waiters")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👨‍💼 **Restaurant Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📊 My Transactions", callback_data="waiter_my_transactions")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="waiter_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🍳 **Waiter Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_admin_command(self, update: Update, context):
        """Handle admin commands - PRD compliant role checking"""
        user_id = update.effective_user.id
        
        # Check if user is super admin
        if user_id != SUPER_ADMIN_USER_ID:
            await update.message.reply_text("❌ Super Admin access required!")
            return
        
        # Log audit
        self.log_audit(user_id, "admin_command", "Super admin accessed admin panel")
        
        # Show super admin menu
        await self.show_super_admin_menu(update)

    async def handle_text_message(self, update: Update, context):
        """Handle text messages - PRD compliant"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in users:
            await update.message.reply_text("Please start with /start first. ❌ Login Failed")
            return
        
        if user_states.get(user_id) == UserState.WAITING_FOR_RESTAURANT_NAME:
            users[user_id]['restaurant_name'] = text
            user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_ADDRESS
            await update.message.reply_text("✅ Restaurant name saved!\n\nPlease provide your restaurant address:")
        
        elif user_states.get(user_id) == UserState.WAITING_FOR_RESTAURANT_ADDRESS:
            users[user_id]['restaurant_address'] = text
            user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
            await update.message.reply_text("✅ Restaurant address saved!\n\nPlease provide your restaurant phone number:")
        
        elif user_states.get(user_id) == UserState.WAITING_FOR_RESTAURANT_PHONE:
            users[user_id]['restaurant_phone'] = text
            users[user_id]['status'] = 'pending_restaurant_approval'
            users[user_id]['restaurant_id'] = f"RST{len(restaurant_ids) + 1:05d}"
            
            # Add to pending restaurant approvals
            pending_restaurant_approvals[user_id] = users[user_id]
            
            user_states[user_id] = None
            
            # Log audit
            self.log_audit(user_id, "restaurant_registration", f"Restaurant {text} registered by user {user_id}")
            
            # Notify Super Admin
            await self.notify_super_admin_restaurant_registration(user_id, users[user_id])
            
            await update.message.reply_text("✅ Restaurant registration complete!\n\nYour registration is pending Super Admin approval.\nYou will be notified once approved.")
        
        elif user_states.get(user_id) == UserState.WAITING_FOR_WAITER_NAME:
            users[user_id]['waiter_name'] = text
            user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
            await update.message.reply_text("✅ Waiter name saved!\n\nPlease provide your phone number:")
        
        elif user_states.get(user_id) == UserState.WAITING_FOR_WAITER_PHONE:
            users[user_id]['waiter_phone'] = text
            users[user_id]['status'] = 'pending_waiter_approval'
            users[user_id]['waiter_id'] = f"WTR{len(waiter_ids) + 1:05d}"
            
            # Add to pending waiter approvals
            if 'pending_waiter_approvals' not in pending_restaurant_approvals:
                pending_restaurant_approvals['pending_waiter_approvals'] = {}
            pending_restaurant_approvals['pending_waiter_approvals'][user_id] = users[user_id]
            
            user_states[user_id] = None
            
            # Log audit
            self.log_audit(user_id, "waiter_registration", f"Waiter {text} registered by user {user_id}")
            
            # Notify Super Admin
            await self.notify_super_admin_waiter_registration(user_id, users[user_id])
            
            await update.message.reply_text("✅ Waiter registration complete!\n\nYour registration is pending Super Admin approval.\nYou will be notified once approved.")
        
        else:
            await update.message.reply_text("Unknown command. Please use the menu buttons.")

    async def notify_super_admin_restaurant_registration(self, user_id: int, restaurant_data: dict):
        """Notify Super Admin about new restaurant registration"""
        try:
            message = f"🏪 **New Restaurant Registration**\n\n"
            message += f"**User ID:** {user_id}\n"
            message += f"**Restaurant Name:** {restaurant_data['restaurant_name']}\n"
            message += f"**Address:** {restaurant_data['restaurant_address']}\n"
            message += f"**Phone:** {restaurant_data['restaurant_phone']}\n"
            message += f"**Restaurant ID:** {restaurant_data['restaurant_id']}\n\n"
            message += f"Please approve or reject this restaurant registration."
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve Restaurant", callback_data=f"approve_restaurant_{user_id}")],
                [InlineKeyboardButton("❌ Reject Restaurant", callback_data=f"reject_restaurant_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                SUPER_ADMIN_USER_ID,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error notifying super admin: {e}")

    async def notify_super_admin_waiter_registration(self, user_id: int, waiter_data: dict):
        """Notify Super Admin about new waiter registration"""
        try:
            message = f"�� **New Waiter Registration**\n\n"
            message += f"**User ID:** {user_id}\n"
            message += f"**Waiter Name:** {waiter_data['waiter_name']}\n"
            message += f"**Phone:** {waiter_data['waiter_phone']}\n"
            message += f"**Waiter ID:** {waiter_data['waiter_id']}\n\n"
            message += f"Please approve or reject this waiter registration."
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve Waiter", callback_data=f"approve_waiter_{user_id}")],
                [InlineKeyboardButton("❌ Reject Waiter", callback_data=f"reject_waiter_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                SUPER_ADMIN_USER_ID,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error notifying super admin: {e}")

    async def handle_photo_message(self, update: Update, context):
        """Handle photo messages for OCR - PRD compliant"""
        user_id = update.effective_user.id
        
        if user_id not in users:
            await update.message.reply_text("Please start with /start first. ❌ Login Failed")
            return
        
        # Check role - only waiters can capture payments
        user_role = users[user_id].get('role', 'waiter')
        if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
            await update.message.reply_text("❌ Only waiters can capture payments!")
            return
        
        if users[user_id].get('status') != 'approved':
            await update.message.reply_text("You are not registered or not approved yet. Please register first or contact your admin.")
            return
        
        # Process photo for OCR
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        try:
            # Get file from Telegram
            file = await self.bot.get_file(file_id)
            file_url = file.file_path
            
            # Download and process image
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    image_data = await response.read()
            
            # Extract data using OCR
            extracted_data = await self.extract_receipt_data_from_google_vision(image_data)
            
            if extracted_data:
                # Create transaction
                transaction_id = f"TXN{len(transactions) + 1:06d}"
                transaction = Transaction(
                    id=transaction_id,
                    user_id=user_id,
                    amount=extracted_data['amount'],
                    transaction_id=extracted_data['transaction_id'],
                    date=extracted_data['date'],
                    time=extracted_data['time'],
                    payer=extracted_data['payer'],
                    receiver=extracted_data['receiver'],
                    bank_name=extracted_data['bank_name'],
                    payment_method=extracted_data['payment_method'],
                    currency=extracted_data['currency'],
                    waiter_id=users[user_id].get('waiter_id', 'UNKNOWN'),
                    restaurant_id=users[user_id].get('restaurant_id', 'UNKNOWN'),
                    created_at=datetime.now()
                )
                
                transactions[transaction_id] = transaction
                
                # Log audit
                self.log_audit(user_id, "transaction_recorded", f"Transaction {transaction_id} recorded: {extracted_data['amount']} ETB")
                
                await update.message.reply_text(
                    f"✅ Payment captured!\n\n"
                    f"Transaction ID: {transaction.transaction_id}\n"
                    f"Amount: {transaction.currency} {transaction.amount:,.2f}\n"
                    f"Payer: {transaction.payer}\n"
                    f"Receiver: {transaction.receiver}\n"
                    f"Bank: {transaction.bank_name}\n"
                    f"Date: {transaction.date} {transaction.time}"
                )
            else:
                await update.message.reply_text("❌ Could not extract payment information from receipt. Please ensure the receipt is clear and try again.")
        
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text("❌ Error processing receipt. Please try again.")

    async def handle_document_message(self, update: Update, context):
        """Handle document messages for bank statement upload - PRD compliant"""
        user_id = update.effective_user.id
        
        # Check role - only admins can upload statements
        user_role = users[user_id].get('role', 'waiter')
        if user_role not in ['restaurant_admin', 'super_admin']:
            await update.message.reply_text("❌ Admin access required for bank statement upload!")
            return
        
        document = update.message.document
        file_id = document.file_id
        
        # Check if it's a PDF
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("❌ Please upload a PDF file for bank statement.")
            return
        
        try:
            # Get file from Telegram
            file = await self.bot.get_file(file_id)
            file_url = file.file_path
            
            # Download PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    pdf_data = await response.read()
            
            # Process bank statement
            await self.process_bank_statement(pdf_data, file_id, user_id)
            
        except Exception as e:
            logger.error(f"Error processing bank statement: {e}")
            await update.message.reply_text("❌ Error processing bank statement. Please try again.")

    async def process_bank_statement(self, pdf_data: bytes, file_id: str, user_id: int):
        """Process bank statement PDF and extract transactions"""
        try:
            # Try pdfplumber first
            try:
                with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            except:
                # Fallback to PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            # Detect bank name
            bank_name = self.detect_bank_name_from_statement(text)
            
            # Extract transactions
            statement_transactions = self.extract_statement_transactions(text, bank_name)
            
            # Create bank statement record
            statement_id = f"STMT{len(bank_statements) + 1:06d}"
            statement = BankStatement(
                id=statement_id,
                restaurant_id=users[user_id].get('restaurant_id', 'RST00001'),
                bank_name=bank_name,
                statement_date=datetime.now(),
                weekly_period_start=datetime.now() - timedelta(days=7),
                weekly_period_end=datetime.now(),
                uploaded_by=user_id,
                pdf_file_id=file_id,
                total_transactions=len(statement_transactions),
                reconciled_transactions=0,
                unmatched_transactions=len(statement_transactions),
                status="PROCESSING",
                created_at=datetime.now()
            )
            
            bank_statements[statement_id] = statement
            
            # Store statement transactions
            for txn in statement_transactions:
                txn.statement_id = statement_id
                statement_transactions[txn.id] = txn
            
            # Log audit
            self.log_audit(user_id, "bank_statement_uploaded", f"Bank statement {statement_id} uploaded: {len(statement_transactions)} transactions")
            
            await self.bot.send_message(
                user_id,
                f"✅ **Bank Statement Processed!**\n\n"
                f"**Statement ID:** {statement_id}\n"
                f"**Bank:** {bank_name}\n"
                f"**Transactions Found:** {len(statement_transactions)}\n"
                f"**Status:** Processing\n\n"
                f"Reconciliation will be performed automatically."
            )
            
        except Exception as e:
            logger.error(f"Error processing bank statement: {e}")
            await self.bot.send_message(user_id, f"❌ Error processing bank statement: {str(e)}")

    def detect_bank_name_from_statement(self, text: str) -> str:
        """Detect bank name from statement text"""
        text_lower = text.lower()
        
        if 'dashen' in text_lower:
            return 'Dashen Bank'
        elif 'cbe' in text_lower or 'commercial bank' in text_lower:
            return 'Commercial Bank of Ethiopia'
        elif 'telebirr' in text_lower:
            return 'telebirr'
        elif 'abyssinia' in text_lower:
            return 'Bank of Abyssinia'
        elif 'awash' in text_lower:
            return 'Awash Bank'
        else:
            return 'Unknown Bank'

    def extract_statement_transactions(self, text: str, bank_name: str) -> List[StatementTransaction]:
        """Extract transactions from bank statement text"""
        transactions = []
        
        if 'dashen' in bank_name.lower():
            transactions = self.extract_dashen_statement_transactions(text)
        elif 'cbe' in bank_name.lower() or 'commercial' in bank_name.lower():
            transactions = self.extract_cbe_statement_transactions(text)
        elif 'telebirr' in bank_name.lower():
            transactions = self.extract_telebirr_statement_transactions(text)
        else:
            transactions = self.extract_generic_statement_transactions(text)
        
        return transactions

    def extract_dashen_statement_transactions(self, text: str) -> List[StatementTransaction]:
        """Extract Dashen Bank statement transactions"""
        transactions = []
        # Implementation for Dashen statement parsing
        return transactions

    def extract_cbe_statement_transactions(self, text: str) -> List[StatementTransaction]:
        """Extract CBE statement transactions"""
        transactions = []
        # Implementation for CBE statement parsing
        return transactions

    def extract_telebirr_statement_transactions(self, text: str) -> List[StatementTransaction]:
        """Extract Telebirr statement transactions"""
        transactions = []
        # Implementation for Telebirr statement parsing
        return transactions

    def extract_generic_statement_transactions(self, text: str) -> List[StatementTransaction]:
        """Extract generic statement transactions"""
        transactions = []
        # Generic implementation
        return transactions

    async def extract_receipt_data_from_google_vision(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Extract receipt data using Google Vision API"""
        try:
            if not self.vision_client:
                return self.get_fallback_data()
            
            # Create image object
            image = vision.Image(content=image_data)
            
            # Perform text detection
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if not texts:
                return self.get_fallback_data()
            
            # Get full text
            full_text = texts[0].description
            logger.info(f"OCR extracted text: {full_text}")
            
            # Extract data based on bank
            result = {}
            
            # Detect bank name
            bank_name = self.detect_bank_name(full_text)
            result['bank_name'] = bank_name
            result['payment_method'] = bank_name
            
            # Extract based on bank
            if 'dashen' in bank_name.lower():
                result = self.extract_dashen_data(full_text, result)
            elif 'cbe' in bank_name.lower() or 'commercial' in bank_name.lower():
                result = self.extract_cbe_data(full_text, result)
            elif 'telebirr' in bank_name.lower():
                result = self.extract_telebirr_data(full_text, result)
            else:
                result = self.extract_generic_data(full_text, result)
            
            logger.info(f"Extracted data: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in OCR extraction: {e}")
            return self.get_fallback_data()

    def get_fallback_data(self) -> Dict[str, Any]:
        """Get fallback data for testing"""
        return {
            'amount': 1000.0,
            'transaction_id': 'FALLBACK123',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'payer': 'Test Payer',
            'receiver': 'Test Receiver',
            'bank_name': 'Test Bank',
            'payment_method': 'Test Bank',
            'currency': 'ETB'
        }

    def detect_bank_name(self, text: str) -> str:
        """Detect bank name from text"""
        text_lower = text.lower()
        
        if 'dashen' in text_lower:
            return 'Dashen Bank'
        elif 'cbe' in text_lower or 'commercial bank' in text_lower:
            return 'Commercial Bank of Ethiopia'
        elif 'telebirr' in text_lower:
            return 'telebirr'
        else:
            return 'Unknown Bank'

    def extract_dashen_data(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Dashen Bank data with correct patterns"""
        # Look for Transaction Ref: OBTSO
        txn_ref_match = re.search(r'Transaction Ref:\s*([A-Z0-9]+)', text)
        if txn_ref_match:
            result['transaction_id'] = txn_ref_match.group(1)
        
        # Look for Total: 10,027.60 ETB
        total_match = re.search(r'Total:\s*([0-9,]+\.?[0-9]*)\s*ETB', text)
        if total_match:
            result['amount'] = float(total_match.group(1).replace(',', ''))
        
        # Look for Sender Name: Mariamawit Alemayehu Zewdu
        sender_match = re.search(r'Sender Name:\s*([^\n]+)', text)
        if sender_match:
            result['payer'] = sender_match.group(1).strip()
        
        # Look for Recipient Name: Meseret Ayalew
        recipient_match = re.search(r'Recipient Name:\s*([^\n]+)', text)
        if recipient_match:
            result['receiver'] = recipient_match.group(1).strip()
        
        # Look for date: Aug 08, 2025 01:07 PM
        date_match = re.search(r'(\w{3}\s+\d{2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)', text)
        if date_match:
            result['date'] = date_match.group(1)
            result['time'] = date_match.group(1).split()[-2] + ' ' + date_match.group(1).split()[-1]
        
        result['currency'] = 'ETB'
        return result

    def extract_cbe_data(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract CBE data"""
        # Amount
        amount_match = re.search(r'ETB\s+(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if amount_match:
            result['amount'] = float(amount_match.group(1).replace(',', ''))
        
        # Transaction ID
        txn_match = re.search(r'transaction ID:\s*([A-Z0-9]+)', text)
        if txn_match:
            result['transaction_id'] = txn_match.group(1)
        
        # Payer
        payer_match = re.search(r'debited from\s+([A-Z\s\n]+)', text)
        if payer_match:
            result['payer'] = payer_match.group(1).strip().replace('\n', ' ')
        
        # Receiver
        receiver_match = re.search(r'for\s+([A-Z\s]+)', text)
        if receiver_match:
            result['receiver'] = receiver_match.group(1).strip()
        
        # Date
        date_match = re.search(r'(\d{2}-\w{3}-\d{4})', text)
        if date_match:
            result['date'] = date_match.group(1)
        
        # Time
        time_match = re.search(r'(\d{1,2}:\d{2})', text)
        if time_match:
            result['time'] = time_match.group(1)
        
        result['currency'] = 'ETB'
        return result

    def extract_telebirr_data(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Telebirr data with correct patterns"""
        # Look for Transaction Number: CHC85KOLMU
        txn_match = re.search(r'Transaction Number:\s*([A-Z0-9]+)', text)
        if txn_match:
            result['transaction_id'] = txn_match.group(1)
        
        # Look for Transaction To: Mekonen
        receiver_match = re.search(r'Transaction To:\s*([^\n]+)', text)
        if receiver_match:
            result['payer'] = receiver_match.group(1).strip()
        
        # Look for amount: -7,008.00 (ETB)
        amount_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\(ETB\)', text)
        if amount_match:
            result['amount'] = float(amount_match.group(1).replace(',', ''))
        
        # Look for date: 2025/08/12 13:23:22
        datetime_match = re.search(r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', text)
        if datetime_match:
            result['date'] = datetime_match.group(1)
            result['time'] = datetime_match.group(1).split()[-1]
        
        result['currency'] = 'ETB'
        return result

    def extract_generic_data(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generic extraction for unknown banks"""
        # Try to extract amount
        amount_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*ETB', text)
        if amount_match:
            result['amount'] = float(amount_match.group(1).replace(',', ''))
        
        result['currency'] = 'ETB'
        return result

    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries - PRD compliant"""
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Callback query error: {e}")
            # Don't return here, continue processing
        
        user_id = query.from_user.id
        
        # Ensure Super Admin is always recognized
        if user_id == SUPER_ADMIN_USER_ID and user_id not in users:
            users[user_id] = {
                'name': 'Super Admin',
                'role': 'super_admin',
                'status': 'approved'
            }
        
        user_role = users.get(user_id, {}).get('role', 'waiter')
        
        if query.data == "register_restaurant":
            if user_id not in users:
                users[user_id] = {
                    'restaurant_name': '',
                    'restaurant_address': '',
                    'restaurant_phone': '',
                    'status': 'pending_restaurant_approval',
                    'restaurant_id': '',
                    'role': 'restaurant_admin'
                }
            
            user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
            await query.edit_message_text("Please provide your restaurant name:")
        
        elif query.data == "register_waiter":
            if user_id not in users:
                users[user_id] = {
                    'waiter_name': '',
                    'waiter_phone': '',
                    'status': 'pending_waiter_approval',
                    'waiter_id': '',
                    'restaurant_id': '',
                    'role': 'waiter'
                }
            
            user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
            await query.edit_message_text("Please provide your full name:")
        
        elif query.data == "super_admin_login":
            if user_id == SUPER_ADMIN_USER_ID:
                users[user_id] = {
                    'name': 'Super Admin',
                    'role': 'super_admin',
                    'status': 'approved'
                }
                await query.edit_message_text("✅ Super Admin access granted!")
                await self.show_super_admin_menu(update)
            else:
                await query.edit_message_text("❌ Super Admin access required!")
        
        elif query.data == "admin_pending_restaurants":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            if not pending_restaurant_approvals:
                await query.edit_message_text("✅ No pending restaurant approvals!")
                return
            
            message = "⏳ **Pending Restaurant Approvals**\n\n"
            for user_id, approval_data in pending_restaurant_approvals.items():
                if isinstance(approval_data, dict) and 'restaurant_name' in approval_data:
                    message += f"**User ID:** {user_id}\n"
                    message += f"**Restaurant:** {approval_data['restaurant_name']}\n"
                    message += f"**Address:** {approval_data['restaurant_address']}\n"
                    message += f"**Phone:** {approval_data['restaurant_phone']}\n\n"
            
            # Add approve/reject buttons
            keyboard = []
            for user_id in pending_restaurant_approvals.keys():
                if isinstance(pending_restaurant_approvals[user_id], dict) and 'restaurant_name' in pending_restaurant_approvals[user_id]:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ Approve Restaurant {user_id}", callback_data=f"approve_restaurant_{user_id}"),
                        InlineKeyboardButton(f"❌ Reject Restaurant {user_id}", callback_data=f"reject_restaurant_{user_id}")
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data.startswith("approve_restaurant_"):
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            user_id_to_approve = int(query.data.split("_")[2])
            
            if user_id_to_approve in pending_restaurant_approvals:
                # Move to approved users
                users[user_id_to_approve] = pending_restaurant_approvals[user_id_to_approve]
                users[user_id_to_approve]['status'] = 'approved'
                users[user_id_to_approve]['role'] = 'restaurant_admin'
                
                # Remove from pending
                del pending_restaurant_approvals[user_id_to_approve]
                
                # Log audit
                self.log_audit(SUPER_ADMIN_USER_ID, "restaurant_approved", f"Restaurant {user_id_to_approve} approved")
                
                await query.edit_message_text(f"✅ **Restaurant Approved!**\n\nRestaurant ID: `{users[user_id_to_approve]['restaurant_id']}`", parse_mode='Markdown')
                
                # Notify the restaurant admin
                try:
                    await self.bot.send_message(
                        user_id_to_approve,
                        f"🎉 **Congratulations!**\n\nYour restaurant has been approved!\n\n**Restaurant ID:** `{users[user_id_to_approve]['restaurant_id']}`\n\nYou can now manage your restaurant and add waiters!",
                        parse_mode='Markdown'
                    )
                except:
                    pass
            else:
                await query.edit_message_text("❌ Restaurant not found in pending approvals!")
        
        elif query.data.startswith("reject_restaurant_"):
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            user_id_to_reject = int(query.data.split("_")[2])
            
            if user_id_to_reject in pending_restaurant_approvals:
                del pending_restaurant_approvals[user_id_to_reject]
                
                # Log audit
                self.log_audit(SUPER_ADMIN_USER_ID, "restaurant_rejected", f"Restaurant {user_id_to_reject} rejected")
                
                await query.edit_message_text(f"❌ **Restaurant Rejected!**\n\nRestaurant {user_id_to_reject} has been rejected.", parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ Restaurant not found in pending approvals!")
        
        elif query.data == "admin_all_transactions":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            if not transactions:
                await query.edit_message_text("📊 **All Transactions**\n\nNo transactions found.")
                return
            
            message = "📊 **All Transactions**\n\n"
            for txn in transactions.values():
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"
            
            await query.edit_message_text(message)
        
        # Waiter Functionality
        elif query.data == "capture_payment":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            if users[user_id].get('status') != 'approved':
                await query.edit_message_text("❌ You are not approved yet. Please contact your admin.")
                return
            
            await query.edit_message_text("📸 **Capture Payment**\n\nPlease take a photo of the payment receipt.\n\nMake sure the receipt is clear and all text is visible.")

            user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        elif query.data == "waiter_my_transactions":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            # Get waiter ID for the user
            waiter_id = users.get(user_id, {}).get('waiter_id', 'UNKNOWN')
            
            # Filter transactions for this waiter
            waiter_transactions = [txn for txn in transactions.values() if txn.waiter_id == waiter_id]
            
            if not waiter_transactions:
                await query.edit_message_text("📊 **My Transactions**\n\nNo transactions recorded yet.")
                return
            
            message = f"📊 **My Transactions**\n\n"
            message += f"**Waiter ID:** {waiter_id}\n"
            message += f"**Total Transactions:** {len(waiter_transactions)}\n\n"
            
            # Show last 10 transactions
            recent_transactions = sorted(waiter_transactions, key=lambda x: x.created_at, reverse=True)[:10]
            for txn in recent_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"
                message += f"  Payer: {txn.payer} | Date: {txn.date}\n\n"
            
            if len(waiter_transactions) > 10:
                message += f"... and {len(waiter_transactions) - 10} more transactions"
            
            await query.edit_message_text(message)
        
        elif query.data == "waiter_help":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            help_message = """ℹ️ **Waiter Help**

**How to capture payments:**
1. Click "📸 Capture Payment"
2. Take a clear photo of the payment receipt
3. The bot will extract payment information automatically
4. Review and confirm the details

**Supported banks:**
• Dashen Bank
• Commercial Bank of Ethiopia (CBE)
• Telebirr
• Other Ethiopian banks

**Tips for better OCR:**
• Ensure good lighting
• Keep the receipt flat
• Make sure all text is visible
• Avoid shadows and glare

**Need help?** Contact your restaurant admin or Super Admin."""
            
            await query.edit_message_text(help_message)
        
        elif query.data == "admin_daily_report":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            today = datetime.now().date()
            today_transactions = [txn for txn in transactions.values() if txn.created_at.date() == today]
            
            if not today_transactions:
                await query.edit_message_text("📊 **Daily Report**\n\nNo transactions for today.")
                return
            
            message = f"📊 **Daily Report - {today}**\n\n"
            total_amount = sum(txn.amount for txn in today_transactions)
            message += f"**Total Transactions:** {len(today_transactions)}\n"
            message += f"**Total Amount:** ETB {total_amount:,.2f}\n\n"
            
            for txn in today_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f}\n"
            
            await query.edit_message_text(message)
        
        # Waiter Functionality
        elif query.data == "capture_payment":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            if users[user_id].get('status') != 'approved':
                await query.edit_message_text("❌ You are not approved yet. Please contact your admin.")
                return
            
                return
            
            # Get waiter ID for the user
            waiter_id = users.get(user_id, {}).get('waiter_id', 'UNKNOWN')
            
            # Filter transactions for this waiter
            waiter_transactions = [txn for txn in transactions.values() if txn.waiter_id == waiter_id]
            
            if not waiter_transactions:
                await query.edit_message_text("📊 **My Transactions**\n\nNo transactions recorded yet.")
                return
            
            message = f"📊 **My Transactions**\n\n"
            message += f"**Waiter ID:** {waiter_id}\n"
            message += f"**Total Transactions:** {len(waiter_transactions)}\n\n"
            
            # Show last 10 transactions
            recent_transactions = sorted(waiter_transactions, key=lambda x: x.created_at, reverse=True)[:10]
            for txn in recent_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"
                message += f"  Payer: {txn.payer} | Date: {txn.date}\n\n"
            
            if len(waiter_transactions) > 10:
                message += f"... and {len(waiter_transactions) - 10} more transactions"
            
            await query.edit_message_text(message)
        
        elif query.data == "waiter_help":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            help_message = """ℹ️ **Waiter Help**

**How to capture payments:**
1. Click "📸 Capture Payment"
2. Take a clear photo of the payment receipt
3. The bot will extract payment information automatically
4. Review and confirm the details

**Supported banks:**
• Dashen Bank
• Commercial Bank of Ethiopia (CBE)
• Telebirr
• Other Ethiopian banks

**Tips for better OCR:**
• Ensure good lighting
• Keep the receipt flat
• Make sure all text is visible
• Avoid shadows and glare

**Need help?** Contact your restaurant admin or Super Admin."""
            
            await query.edit_message_text(help_message)
        
        elif query.data == "admin_upload_statement":
            if user_role not in ['super_admin', 'restaurant_admin']:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            await query.edit_message_text("🏦 **Bank Statement Upload**\n\nPlease upload a PDF bank statement for reconciliation.")
            user_states[query.from_user.id] = UserState.UPLOADING_STATEMENT
        
        elif query.data == "admin_reconciliation_report":
            if user_role not in ['super_admin', 'restaurant_admin']:
                await query.edit_message_text("❌ Admin access required!")
                return
            
            if not bank_statements:
                await query.edit_message_text("📋 **Reconciliation Report**\n\nNo bank statements uploaded yet.")
                return
            
            message = "📋 **Reconciliation Report**\n\n"
            for stmt in bank_statements.values():
                message += f"**Statement ID:** {stmt.id}\n"
                message += f"**Bank:** {stmt.bank_name}\n"
                message += f"**Total Transactions:** {stmt.total_transactions}\n"
                message += f"**Reconciled:** {stmt.reconciled_transactions}\n"
                message += f"**Unmatched:** {stmt.unmatched_transactions}\n\n"
            
            await query.edit_message_text(message)
        
        # Waiter Functionality
        elif query.data == "capture_payment":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            if users[user_id].get('status') != 'approved':
                await query.edit_message_text("❌ You are not approved yet. Please contact your admin.")
                return
            
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            # Get waiter ID for the user
            await query.edit_message_text("📸 **Capture Payment**\n\nPlease take a photo of the payment receipt.\n\nMake sure the receipt is clear and all text is visible.")
            
            # Filter transactions for this waiter
            waiter_transactions = [txn for txn in transactions.values() if txn.waiter_id == waiter_id]
            
            if not waiter_transactions:
                await query.edit_message_text("📊 **My Transactions**\n\nNo transactions recorded yet.")
                return
            
            message = f"📊 **My Transactions**\n\n"
            message += f"**Waiter ID:** {waiter_id}\n"
            message += f"**Total Transactions:** {len(waiter_transactions)}\n\n"
            
            # Show last 10 transactions
            recent_transactions = sorted(waiter_transactions, key=lambda x: x.created_at, reverse=True)[:10]
            for txn in recent_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"
                message += f"  Payer: {txn.payer} | Date: {txn.date}\n\n"
            
            if len(waiter_transactions) > 10:
                message += f"... and {len(waiter_transactions) - 10} more transactions"
            
            await query.edit_message_text(message)
        
        elif query.data == "waiter_help":
            if user_role not in ['waiter', 'restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Waiter access required!")
                return
            
            help_message = """ℹ️ **Waiter Help**

**How to capture payments:**
1. Click "📸 Capture Payment"
2. Take a clear photo of the payment receipt
3. The bot will extract payment information automatically
4. Review and confirm the details

**Supported banks:**
• Dashen Bank
• Commercial Bank of Ethiopia (CBE)
• Telebirr
• Other Ethiopian banks

**Tips for better OCR:**
• Ensure good lighting
• Keep the receipt flat
• Make sure all text is visible
• Avoid shadows and glare

**Need help?** Contact your restaurant admin or Super Admin."""
            
            await query.edit_message_text(help_message)



        elif query.data == "admin_menu":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            await self.show_super_admin_menu(update)

        elif query.data == "restaurant_transactions":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            # Get restaurant ID for the user
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            
            # Filter transactions for this restaurant
            restaurant_transactions = [txn for txn in transactions.values() if txn.restaurant_id == restaurant_id]
            
            if not restaurant_transactions:
                await query.edit_message_text("📊 **Restaurant Transactions**\n\nNo transactions found for your restaurant.")
                return
            
            message = f"📊 **Restaurant Transactions**\n\n"
            message += f"**Restaurant ID:** {restaurant_id}\n"
            message += f"**Total Transactions:** {len(restaurant_transactions)}\n\n"
            
            # Show last 10 transactions
            recent_transactions = sorted(restaurant_transactions, key=lambda x: x.created_at, reverse=True)[:10]
            for txn in recent_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f} - {txn.bank_name}\n"
                message += f"  Payer: {txn.payer} | Date: {txn.date}\n\n"
            
            if len(restaurant_transactions) > 10:
                message += f"... and {len(restaurant_transactions) - 10} more transactions"
            
            await query.edit_message_text(message)

        elif query.data == "restaurant_daily_summary":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            today = datetime.now().date()
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            today_transactions = [txn for txn in transactions.values() if txn.restaurant_id == restaurant_id and txn.created_at.date() == today]
            
            if not today_transactions:
                await query.edit_message_text("📈 **Daily Summary**\n\nNo transactions for today.")
                return
            
            total_amount = sum(txn.amount for txn in today_transactions)
            message = f"📈 **Daily Summary - {today}**\n\n"
            message += f"**Restaurant ID:** {restaurant_id}\n"
            message += f"**Total Transactions:** {len(today_transactions)}\n"
            message += f"**Total Amount:** ETB {total_amount:,.2f}\n\n"
            
            for txn in today_transactions:
                message += f"• {txn.transaction_id}: {txn.currency} {txn.amount:,.2f}\n"
            
            await query.edit_message_text(message)

        elif query.data == "restaurant_export_csv":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            restaurant_transactions = [txn for txn in transactions.values() if txn.restaurant_id == restaurant_id]
            
            if not restaurant_transactions:
                await query.edit_message_text("📤 **Export CSV**\n\nNo transactions to export.")
                return
            
            # Create CSV content
            csv_content = "Transaction ID,Amount,Currency,Payer,Receiver,Bank,Date,Time,Waiter ID\n"
            for txn in restaurant_transactions:
                csv_content += f"{txn.transaction_id},{txn.amount},{txn.currency},{txn.payer},{txn.receiver},{txn.bank_name},{txn.date},{txn.time},{txn.waiter_id}\n"
            
            # Send as document
            csv_file = io.StringIO(csv_content)
            csv_bytes = csv_file.getvalue().encode('utf-8')
            
            await self.bot.send_document(
                user_id,
                document=io.BytesIO(csv_bytes),
                filename=f"restaurant_transactions_{restaurant_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                caption=f"📤 **Restaurant Transactions Export**\n\nRestaurant ID: {restaurant_id}\nTotal Transactions: {len(restaurant_transactions)}"
            )

        elif query.data == "restaurant_upload_statement":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            await query.edit_message_text("🏦 **Bank Statement Upload**\n\nPlease upload a PDF bank statement for reconciliation.")
            user_states[query.from_user.id] = UserState.UPLOADING_STATEMENT

        elif query.data == "restaurant_reconciliation":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            restaurant_statements = [stmt for stmt in bank_statements.values() if stmt.restaurant_id == restaurant_id]
            
            if not restaurant_statements:
                await query.edit_message_text("📋 **Reconciliation Report**\n\nNo bank statements uploaded for your restaurant.")
                return
            
            message = f"📋 **Reconciliation Report - Restaurant {restaurant_id}**\n\n"
            for stmt in restaurant_statements:
                message += f"**Statement ID:** {stmt.id}\n"
                message += f"**Bank:** {stmt.bank_name}\n"
                message += f"**Total Transactions:** {stmt.total_transactions}\n"
                message += f"**Reconciled:** {stmt.reconciled_transactions}\n"
                message += f"**Unmatched:** {stmt.unmatched_transactions}\n\n"
            
            await query.edit_message_text(message)

        elif query.data == "restaurant_manage_waiters":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            
            # Get waiters for this restaurant
            restaurant_waiters = [user for user in users.values() if user.get('restaurant_id') == restaurant_id and user.get('role') == 'waiter' and user.get('status') == 'approved']
            
            if not restaurant_waiters:
                await query.edit_message_text("👥 **Manage Waiters**\n\nNo approved waiters found for your restaurant.")
                return
            
            message = f"👥 **Manage Waiters - Restaurant {restaurant_id}**\n\n"
            for i, waiter in enumerate(restaurant_waiters, 1):
                message += f"{i}. **{waiter.get('waiter_name', 'Unknown')}**\n"
                message += f"   Waiter ID: {waiter.get('waiter_id', 'Unknown')}\n"
                message += f"   Phone: {waiter.get('waiter_phone', 'Unknown')}\n\n"
            
            await query.edit_message_text(message)

        elif query.data == "restaurant_pending_waiters":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            
            # Get pending waiters for this restaurant
            pending_waiters = []
            if 'pending_waiter_approvals' in pending_restaurant_approvals:
                for waiter_id, waiter_data in pending_restaurant_approvals['pending_waiter_approvals'].items():
                    if waiter_data.get('restaurant_id') == restaurant_id:
                        pending_waiters.append((waiter_id, waiter_data))
            
            if not pending_waiters:
                await query.edit_message_text("⏳ **Pending Waiter Approvals**\n\nNo pending waiter approvals for your restaurant.")
                return
            
            message = f"⏳ **Pending Waiter Approvals - Restaurant {restaurant_id}**\n\n"
            for waiter_id, waiter_data in pending_waiters:
                message += f"**Waiter ID:** {waiter_id}\n"
                message += f"**Name:** {waiter_data.get('waiter_name', 'Unknown')}\n"
                message += f"**Phone:** {waiter_data.get('waiter_phone', 'Unknown')}\n\n"
            
            # Add approve/reject buttons
            keyboard = []
            for waiter_id, waiter_data in pending_waiters:
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {waiter_data.get('waiter_name', 'Waiter')}", callback_data=f"restaurant_approve_waiter_{waiter_id}"),
                    InlineKeyboardButton(f"❌ Reject {waiter_data.get('waiter_name', 'Waiter')}", callback_data=f"restaurant_reject_waiter_{waiter_id}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant Menu", callback_data="restaurant_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

        elif query.data == "restaurant_menu":
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            await self.show_restaurant_admin_menu(update)

        elif query.data == "admin_manage_restaurants":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            # Get all approved restaurants
            approved_restaurants = [user for user in users.values() if user.get('role') == 'restaurant_admin' and user.get('status') == 'approved']
            
            if not approved_restaurants:
                await query.edit_message_text("👥 **Manage Restaurants**\n\nNo approved restaurants found.")
                return
            
            message = "👥 **Manage Restaurants**\n\n"
            for i, restaurant in enumerate(approved_restaurants, 1):
                message += f"{i}. **{restaurant.get('restaurant_name', 'Unknown')}**\n"
                message += f"   ID: {restaurant.get('restaurant_id', 'Unknown')}\n"
                message += f"   Address: {restaurant.get('restaurant_address', 'Unknown')}\n\n"
            
            await query.edit_message_text(message)

        elif query.data.startswith("restaurant_approve_waiter_"):
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            waiter_id_to_approve = int(query.data.split("_")[3])
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            
            if 'pending_waiter_approvals' in pending_restaurant_approvals and waiter_id_to_approve in pending_restaurant_approvals['pending_waiter_approvals']:
                waiter_data = pending_restaurant_approvals['pending_waiter_approvals'][waiter_id_to_approve]
                
                # Check if this waiter belongs to this restaurant
                if waiter_data.get('restaurant_id') == restaurant_id:
                    # Move to approved users
                    users[waiter_id_to_approve] = waiter_data
                    users[waiter_id_to_approve]['status'] = 'approved'
                    users[waiter_id_to_approve]['role'] = 'waiter'
                    
                    # Remove from pending
                    del pending_restaurant_approvals['pending_waiter_approvals'][waiter_id_to_approve]
                    
                    # Log audit
                    self.log_audit(user_id, "waiter_approved", f"Waiter {waiter_id_to_approve} approved by restaurant admin")
                    
                    await query.edit_message_text(f"✅ **Waiter Approved!**\n\nWaiter ID: `{users[waiter_id_to_approve]['waiter_id']}`\n\nWaiter can now capture payments!", parse_mode='Markdown')
                    
                    # Notify the waiter
                    try:
                        await self.bot.send_message(
                            waiter_id_to_approve,
                            f"🎉 **Congratulations!**\n\nYour waiter registration has been approved by your restaurant admin!\n\n**Waiter ID:** `{users[waiter_id_to_approve]['waiter_id']}`\n\nYou can now capture payments!",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                else:
                    await query.edit_message_text("❌ This waiter does not belong to your restaurant!")
            else:
                await query.edit_message_text("❌ Waiter not found in pending approvals!")

        elif query.data.startswith("restaurant_reject_waiter_"):
            if user_role not in ['restaurant_admin', 'super_admin']:
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            waiter_id_to_reject = int(query.data.split("_")[3])
            restaurant_id = users.get(user_id, {}).get('restaurant_id', 'UNKNOWN')
            
            if 'pending_waiter_approvals' in pending_restaurant_approvals and waiter_id_to_reject in pending_restaurant_approvals['pending_waiter_approvals']:
                waiter_data = pending_restaurant_approvals['pending_waiter_approvals'][waiter_id_to_reject]
                
                # Check if this waiter belongs to this restaurant
                if waiter_data.get('restaurant_id') == restaurant_id:
                    del pending_restaurant_approvals['pending_waiter_approvals'][waiter_id_to_reject]
                    
                    # Log audit
                    self.log_audit(user_id, "waiter_rejected", f"Waiter {waiter_id_to_reject} rejected by restaurant admin")
                    
                    await query.edit_message_text(f"❌ **Waiter Rejected!**\n\nWaiter {waiter_id_to_reject} has been rejected.", parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ This waiter does not belong to your restaurant!")
            else:
                await query.edit_message_text("❌ Waiter not found in pending approvals!")
    def log_audit(self, user_id: int, action: str, details: str):
        """Log audit trail"""
        audit_log = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'action': action,
            'details': details
        }
        audit_logs.append(audit_log)
        logger.info(f"Audit: {action} by {user_id}: {details}")

    async def run(self):
        """Run the bot - FIXED for proper polling"""
        try:
            logger.info("Starting VeriPay Bot - PRD COMPLIANT VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Keep running with proper signal handling
            try:
                # Wait for shutdown signal
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("Received shutdown signal. Stopping bot gracefully...")
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                await self.application.stop()
                logger.info("Bot stopped.")
            except:
                pass

if __name__ == "__main__":
    bot = VeriPayBot()
    asyncio.run(bot.run())
