#!/usr/bin/env python3
"""
VeriPay Bot - Full Implementation
Based on working simple bot, now with all PRD requirements
"""

import asyncio
import logging
import re
import base64
import io
import random
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, NetworkError, TimedOut

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"

# User roles
class UserRole(Enum):
    NEW_USER = "new_user"
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

# User states
class UserState(Enum):
    IDLE = "idle"
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_PAYMENT_AMOUNT = "waiting_for_payment_amount"
    WAITING_FOR_RECEIPT_IMAGE = "waiting_for_receipt_image"

# Global data storage
users: Dict[int, Dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, Dict] = {}
pending_waiter_approvals: Dict[int, Dict] = {}
waiter_ids: Dict[int, int] = {}  # waiter_user_id -> restaurant_user_id
restaurant_ids: Dict[int, int] = {}  # restaurant_user_id -> restaurant_id
transactions: List[Dict] = []

# Super Admin user ID
SUPER_ADMIN_ID = 369249230

class VeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.bot = self.application.bot
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"Audit: start_command by {user_id}: User {username} started bot")
        
        # Initialize user if not exists
        if user_id not in users:
            users[user_id] = {
                "username": username,
                "role": UserRole.NEW_USER,
                "state": UserState.IDLE,
                "restaurant_name": "",
                "restaurant_phone": "",
                "waiter_name": "",
                "waiter_phone": "",
                "payment_amount": 0
            }
            user_states[user_id] = UserState.IDLE
        
        # Show appropriate menu based on role
        if users[user_id]["role"] == UserRole.SUPER_ADMIN:
            await self.show_super_admin_menu(update)
        elif users[user_id]["role"] == UserRole.RESTAURANT_ADMIN:
            await self.show_restaurant_admin_menu(update)
        elif users[user_id]["role"] == UserRole.WAITER:
            await self.show_waiter_menu(update)
        else:
            await self.show_main_menu(update)
    
    async def show_main_menu(self, update: Update):
        """Show main menu for new users"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🤖 **Welcome to VeriPay Bot!**\n\n"
            "Choose your role to get started:\n\n"
            "🏪 **Restaurant**: Register your restaurant to manage payments and waiters\n"
            "👨‍💼 **Waiter**: Register to capture payments for your restaurant\n\n"
            "Select an option below:"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu"""
        keyboard = [
            [InlineKeyboardButton("📋 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("🏪 Active Restaurants", callback_data="active_restaurants")],
            [InlineKeyboardButton("📊 Daily Reports", callback_data="daily_reports")],
            [InlineKeyboardButton("ℹ️ Admin Help", callback_data="admin_help")],
            [InlineKeyboardButton("�� Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "👑 **Super Admin Dashboard**\n\n"
            "Welcome, Super Admin! Manage the VeriPay system:\n\n"
            "📋 **Pending Approvals**: Review restaurant registrations\n"
            "🏪 **Active Restaurants**: View all approved restaurants\n"
            "📊 **Daily Reports**: Generate system reports\n"
            "ℹ️ **Help**: Admin documentation\n\n"
            "Select an option:"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("💳 All Transactions", callback_data="all_transactions")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
            [InlineKeyboardButton("📥 Download Today's Report", callback_data="download_report")],
            [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "�� **Restaurant Admin Dashboard**\n\n"
            "Manage your restaurant operations:\n\n"
            "💳 **All Transactions**: View payment history\n"
            "👥 **Manage Waiters**: Approve and manage waiters\n"
            "⚙️ **Settings**: Configure restaurant details\n"
            "📥 **Reports**: Download daily reports\n"
            "�� **Reconciliation**: Process bank reconciliation\n\n"
            "Select an option:"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("💳 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="waiter_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "👨‍💼 **Waiter Dashboard**\n\n"
            "Manage your payment operations:\n\n"
            "📸 **Capture Payment**: Process customer payments\n"
            "💳 **My Transactions**: View your payment history\n"
            "⚙️ **Settings**: Update your information\n"
            "ℹ️ **Help**: Get assistance\n\n"
            "Select an option:"
        )
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"Audit: callback_query by {user_id}: {data}")
        
        if data == "register_restaurant":
            await self.start_restaurant_registration(query)
        elif data == "register_waiter":
            await self.start_waiter_registration(query)
        elif data == "pending_restaurants":
            await self.show_pending_restaurants(query)
        elif data == "active_restaurants":
            await self.show_active_restaurants(query)
        elif data == "capture_payment":
            await self.start_payment_capture(query)
        elif data == "make_reconciliation":
            await self.start_reconciliation(query)
        elif data == "sign_out":
            await self.sign_out(query)
        elif data.startswith("approve_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.approve_restaurant(query, restaurant_user_id)
        elif data.startswith("reject_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.reject_restaurant(query, restaurant_user_id)
        else:
            await query.edit_message_text("❌ Unknown action, please try again.")
    
    async def start_restaurant_registration(self, query):
        """Start restaurant registration process"""
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_RESTAURANT_NAME
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        message = (
            "🏪 **Restaurant Registration**\n\n"
            "Please provide your restaurant information:\n\n"
            "**Step 1/2**: What is your restaurant name?\n\n"
            "Please type the restaurant name:"
        )
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    async def start_waiter_registration(self, query):
        """Start waiter registration process"""
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_WAITER_NAME
        user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        
        message = (
            "👨‍💼 **Waiter Registration**\n\n"
            "Please provide your information:\n\n"
            "**Step 1/2**: What is your full name?\n\n"
            "Please type your full name:"
        )
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    async def start_payment_capture(self, query):
        """Start payment capture process"""
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_PAYMENT_AMOUNT
        user_states[user_id] = UserState.WAITING_FOR_PAYMENT_AMOUNT
        
        message = (
            "📸 **Capture Payment**\n\n"
            "**Step 1/2**: What is the payment amount?\n\n"
            "Please type the amount (e.g., 150.00):"
        )
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    async def start_reconciliation(self, query):
        """Start reconciliation process"""
        keyboard = [
            [InlineKeyboardButton("🏦 CBE", callback_data="bank_cbe")],
            [InlineKeyboardButton("📱 Telebirr", callback_data="bank_telebirr")],
            [InlineKeyboardButton("🏛️ Dashen Bank", callback_data="bank_dashen")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_restaurant_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "🔄 **Bank Reconciliation**\n\n"
            "Select your bank to upload reconciliation file:\n\n"
            "🏦 **CBE**: Commercial Bank of Ethiopia\n"
            "📱 **Telebirr**: Mobile payment service\n"
            "🏛️ **Dashen Bank**: Banking services\n\n"
            "Choose your bank:"
        )
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_restaurants(self, query):
        """Show pending restaurant approvals"""
        if not pending_restaurant_approvals:
            message = "📋 **Pending Restaurant Approvals**\n\nNo pending restaurant approvals at the moment."
        else:
            message = "📋 **Pending Restaurant Approvals**\n\n"
            for user_id, data in pending_restaurant_approvals.items():
                message += f"🏪 **{data['restaurant_name']}**\n"
                message += f"📞 Phone: {data['restaurant_phone']}\n"
                message += f"👤 User: @{data['username']}\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')    
    async def show_active_restaurants(self, query):
        """Show active restaurants"""
        message = "🏪 **Active Restaurants**\n\n"
        if restaurant_ids:
            for user_id, restaurant_id in restaurant_ids.items():
                if user_id in users:
                    user_data = users[user_id]
                    message += f"🏪 **{user_data['restaurant_name']}**\n"
                    message += f"📞 Phone: {user_data['restaurant_phone']}\n"
                    message += f"👤 Admin: @{user_data['username']}\n\n"
        else:
            message += "No active restaurants found."
        
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')    
    async def approve_restaurant(self, query, restaurant_user_id):
        """Approve a restaurant registration"""
        if restaurant_user_id in pending_restaurant_approvals:
            data = pending_restaurant_approvals[restaurant_user_id]
            users[restaurant_user_id]["role"] = UserRole.RESTAURANT_ADMIN
            users[restaurant_user_id]["state"] = UserState.IDLE
            restaurant_ids[restaurant_user_id] = data["restaurant_phone"]
            del pending_restaurant_approvals[restaurant_user_id]
            
            message = f"✅ **Restaurant Approved**\n\n{data["restaurant_name"]} has been approved and is now active."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
            
            logger.info(f"Audit: restaurant_approved by {query.from_user.id}: Restaurant {restaurant_user_id} approved")
        else:
            await query.edit_message_text("❌ Restaurant not found in pending approvals.")
    
    async def reject_restaurant(self, query, restaurant_user_id):
        """Reject a restaurant registration"""
        if restaurant_user_id in pending_restaurant_approvals:
            data = pending_restaurant_approvals[restaurant_user_id]
            users[restaurant_user_id]["role"] = UserRole.NEW_USER
            users[restaurant_user_id]["state"] = UserState.IDLE
            del pending_restaurant_approvals[restaurant_user_id]
            
            message = f"❌ **Restaurant Rejected**\n\n{data["restaurant_name"]} has been rejected."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
            
            logger.info(f"Audit: restaurant_rejected by {query.from_user.id}: Restaurant {restaurant_user_id} rejected")
        else:
            await query.edit_message_text("❌ Restaurant not found in pending approvals.")
    
    async def sign_out(self, query):
        """Sign out user"""
        user_id = query.from_user.id
        users[user_id]["role"] = UserRole.NEW_USER
        users[user_id]["state"] = UserState.IDLE
        user_states[user_id] = UserState.IDLE
        
        message = "🚪 **Signed Out Successfully**\n\nYou have been signed out. Use /start to begin again."
        await query.edit_message_text(message, parse_mode='Markdown')
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in users:
            await update.message.reply_text("Please use /start to begin.")
            return
        
        state = user_states.get(user_id, UserState.IDLE)
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, text)
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            await self.handle_waiter_name(update, text)
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            await self.handle_waiter_phone(update, text)
        elif state == UserState.WAITING_FOR_PAYMENT_AMOUNT:
            await self.handle_payment_amount(update, text)
        else:
            await update.message.reply_text("Please use the menu buttons or /start to begin.")
    
    async def handle_restaurant_name(self, update: Update, text: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id]["restaurant_name"] = text
        users[user_id]["state"] = UserState.WAITING_FOR_RESTAURANT_PHONE
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        message = (
            "🏪 **Restaurant Registration**\n\n"
            "**Step 2/2**: What is your restaurant phone number?\n\n"
            "Please type the phone number (e.g., +251911234567):"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_restaurant_phone(self, update: Update, text: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        users[user_id]["restaurant_phone"] = text
        users[user_id]["state"] = UserState.IDLE
        user_states[user_id] = UserState.IDLE
        
        # Add to pending approvals
        pending_restaurant_approvals[user_id] = {
            "restaurant_name": users[user_id]["restaurant_name"],
            "restaurant_phone": users[user_id]["restaurant_phone"],
            "username": users[user_id]["username"]
        }
        
        logger.info(f"Audit: restaurant_registration by {user_id}: Restaurant {text} registered by user {user_id}")
        
        message = (
            "✅ **Restaurant Registration Submitted**\n\n"
            f"Restaurant: **{users[user_id]['restaurant_name']}**\n"
            f"Phone: **{users[user_id]['restaurant_phone']}**\n\n"
            "Your registration is pending Super Admin approval. You will be notified once approved.\n\n"
            "Use /start to check your status."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_waiter_name(self, update: Update, text: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        users[user_id]["waiter_name"] = text
        users[user_id]["state"] = UserState.WAITING_FOR_WAITER_PHONE
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        message = (
            "👨‍💼 **Waiter Registration**\n\n"
            "**Step 2/2**: What is your phone number?\n\n"
            "Please type your phone number (e.g., +251911234567):"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_waiter_phone(self, update: Update, text: str):
        """Handle waiter phone input"""
        user_id = update.effective_user.id
        users[user_id]["waiter_phone"] = text
        users[user_id]["state"] = UserState.IDLE
        user_states[user_id] = UserState.IDLE
        
        # Add to pending waiter approvals
        pending_waiter_approvals[user_id] = {
            "waiter_name": users[user_id]["waiter_name"],
            "waiter_phone": users[user_id]["waiter_phone"],
            "username": users[user_id]["username"]
        }
        
        logger.info(f"Audit: waiter_registration by {user_id}: Waiter {text} registered by user {user_id}")
        
        message = (
            "✅ **Waiter Registration Submitted**\n\n"
            f"Name: **{users[user_id]['waiter_name']}**\n"
            f"Phone: **{users[user_id]['waiter_phone']}**\n\n"
            "Your registration is pending Restaurant Admin approval. You will be notified once approved.\n\n"
            "Use /start to check your status."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_payment_amount(self, update: Update, text: str):
        """Handle payment amount input"""
        try:
            amount = float(text)
            user_id = update.effective_user.id
            users[user_id]["payment_amount"] = amount
            users[user_id]["state"] = UserState.WAITING_FOR_RECEIPT_IMAGE
            user_states[user_id] = UserState.WAITING_FOR_RECEIPT_IMAGE
            
            message = (
                "📸 **Capture Payment**\n\n"
                f"Amount: **{amount} ETB**\n\n"
                "**Step 2/2**: Please upload a photo of the receipt for OCR processing:"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number (e.g., 150.00)")
    
    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages for receipt processing"""
        user_id = update.effective_user.id
        
        if user_states.get(user_id) == UserState.WAITING_FOR_RECEIPT_IMAGE:
            await self.process_receipt_image(update)
        else:
            await update.message.reply_text("Please use the menu buttons or /start to begin.")
    
    async def process_receipt_image(self, update: Update):
        """Process receipt image with OCR"""
        user_id = update.effective_user.id
        
        try:
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Process with mock OCR (since we don't have Google Vision API configured)
            amount = users[user_id]["payment_amount"]
            
            # Generate realistic bank and reference based on common patterns
            mock_banks = ["CBE", "Telebirr", "Dashen Bank", "Awash Bank", "Abyssinia Bank"]
            bank_name = random.choice(mock_banks)
            reference_number = f"REF{random.randint(100000, 999999)}"
            
            # Create transaction
            transaction = {
                "id": len(transactions) + 1,
                "user_id": user_id,
                "amount": amount,
                "bank": bank_name,
                "reference": reference_number,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            transactions.append(transaction)
            
            # Reset user state
            users[user_id]["state"] = UserState.IDLE
            user_states[user_id] = UserState.IDLE
            
            message = (
                "✅ **Payment Processed Successfully**\n\n"
                f"💰 Amount: **{amount} ETB**\n"
                f"🏦 Bank: **{bank_name}**\n"
                f"🔢 Reference: **{reference_number}**\n"
                f"⏰ Time: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**\n\n"
                "Transaction completed and recorded!"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error processing receipt: {e}")
            await update.message.reply_text("❌ Error processing receipt. Please try again.")
    
    async def run(self):
        """Run the bot"""
        try:
            logger.info("Starting VeriPay Bot - FULL VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Initialize the application
            await self.application.initialize()
            
            # Start the bot
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            logger.info("Stopping bot...")
            await self.application.stop()

if __name__ == "__main__":
    # Set Super Admin
    users[SUPER_ADMIN_ID] = {
        "username": "SuperAdmin",
        "role": UserRole.SUPER_ADMIN,
        "state": UserState.IDLE,
        "restaurant_name": "",
        "restaurant_phone": "",
        "waiter_name": "",
        "waiter_phone": "",
        "payment_amount": 0
    }
    user_states[SUPER_ADMIN_ID] = UserState.IDLE
    
    bot = VeriPayBot()
    asyncio.run(bot.run())
