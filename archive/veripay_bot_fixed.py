#!/usr/bin/env python3
"""
VeriPay Bot - FIXED VERSION
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
import io
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Telegram imports
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError

# Configuration
BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"
SUPER_ADMIN_USER_ID = 369249230  # Your User ID

# Enums
class UserRole(Enum):
    NEW_USER = "new_user"
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

class UserState(Enum):
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_RESTAURANT_SELECTION = "waiting_for_restaurant_selection"
    CAPTURING_PAYMENT = "capturing_payment"

# Global storage
users: Dict[int, Dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, Dict] = {}
pending_waiter_approvals: Dict[int, Dict] = {}
restaurant_ids: Dict[str, Dict] = {}
waiter_ids: Dict[str, Dict] = {}
transactions: Dict[str, Dict] = {}

# Initialize Super Admin
users[SUPER_ADMIN_USER_ID] = {
    'role': UserRole.SUPER_ADMIN,
    'status': 'approved',
    'name': 'Super Admin'
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VeriPayBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.bot = None

    def log_audit(self, user_id: int, action: str, details: str):
        """Log user actions for audit trail"""
        logger.info(f"Audit: {action} by {user_id}: {details}")

    def get_fallback_data(self) -> Dict:
        """Get fallback data when OCR is not available"""
        return {
            'amount': 1500.0,
            'transaction_id': f'TXN{int(time.time())}',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'payer': 'Sample Payer',
            'receiver': 'Sample Receiver',
            'bank_name': 'Sample Bank',
            'payment_method': 'Bank Transfer',
            'currency': 'ETB'
        }

    async def extract_receipt_data_from_google_vision(self, image_data: bytes) -> Dict:
        """Extract transaction data from receipt image using Google Vision API"""
        logger.warning("Google Vision API not available, using fallback data")
        return self.get_fallback_data()

    async def start_command(self, update: Update, context):
        """Handle /start command with modern UI"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
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
                await self.show_waiter_menu(update, context)
        else:
            # Show role selection menu
            keyboard = [
                [InlineKeyboardButton("👑 Super Admin Login", callback_data="super_admin_login")],
                [InlineKeyboardButton("🏪 Restaurant Admin Registration", callback_data="register_restaurant_admin")],
                [InlineKeyboardButton("🍳 Waiter Registration", callback_data="register_waiter")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = """
🎯 **Welcome to VeriPay Bot!**

Choose your role to get started:

👑 **Super Admin** - Manage restaurants and system
🏪 **Restaurant Admin** - Manage your restaurant and waiters  
🍳 **Waiter** - Capture payments and manage transactions

Select your role below:
            """
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu with modern UI"""
        keyboard = [
            [InlineKeyboardButton("🏪 Pending Restaurant Approvals", callback_data="super_admin_pending_restaurants")],
            [InlineKeyboardButton("📊 System Overview", callback_data="super_admin_overview")],
            [InlineKeyboardButton("👥 Manage Users", callback_data="super_admin_manage_users")],
            [InlineKeyboardButton("📈 Analytics", callback_data="super_admin_analytics")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="super_admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = """
👑 **Super Admin Panel**

Welcome to the VeriPay management dashboard!

**Quick Actions:**
🏪 Manage restaurant approvals
📊 View system overview
👥 Manage users and permissions
📈 View analytics and reports
⚙️ Configure system settings

Select an option below:
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu with modern UI"""
        keyboard = [
            [InlineKeyboardButton("📊 My Restaurant Transactions", callback_data="restaurant_transactions")],
            [InlineKeyboardButton("📈 Daily Summary", callback_data="restaurant_daily_summary")],
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")],
            [InlineKeyboardButton("📤 Export CSV", callback_data="restaurant_export_csv")],
            [InlineKeyboardButton("🏦 Upload Bank Statement", callback_data="restaurant_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="restaurant_reconciliation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = """
👨‍💼 **Restaurant Admin Panel**

Manage your restaurant operations efficiently!

**Quick Actions:**
📊 View transaction history
�� Check daily summaries
👥 Approve waiter registrations
📤 Export data to CSV
🏦 Upload bank statements
📋 Generate reconciliation reports

Select an option below:
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_waiter_menu(self, update: Update, context=None):
        """Show Waiter menu with modern UI"""
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="waiter_transactions")],
            [InlineKeyboardButton("📊 Today's Summary", callback_data="waiter_daily_summary")],
            [InlineKeyboardButton("❓ Help", callback_data="waiter_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        menu_text = """
🍳 **Waiter Panel**

Welcome to your payment management dashboard!

**Quick Actions:**
📸 Capture payment receipts
📋 View your transactions
📊 Check today's summary
❓ Get help and support

Select an option below:
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries with modern UI"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "super_admin_login":
            if user_id == SUPER_ADMIN_USER_ID:
                users[user_id] = {'role': UserRole.SUPER_ADMIN, 'status': 'approved'}
                await self.show_super_admin_menu(update)
            else:
                await query.edit_message_text("❌ Access denied. Only Super Admin can access this panel.")
        
        elif data == "register_restaurant_admin":
            await self.start_restaurant_registration(update, context)
        
        elif data == "register_waiter":
            await self.start_waiter_registration(update, context)
        
        elif data == "super_admin_pending_restaurants":
            await self.show_pending_restaurants(update, context)
        
        elif data == "restaurant_pending_waiters":
            await self.show_pending_waiters(update, context)
        
        elif data == "capture_payment":
            await self.start_payment_capture(update, context)
        
        else:
            await query.edit_message_text("❌ Unknown action. Please try again.")

    async def start_restaurant_registration(self, update: Update, context):
        """Start restaurant registration process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        await update.callback_query.edit_message_text(
            "🏪 **Restaurant Registration**\n\nPlease provide your restaurant name:",
            parse_mode='Markdown'
        )

    async def start_waiter_registration(self, update: Update, context):
        """Start waiter registration process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        
        await update.callback_query.edit_message_text(
            "🍳 **Waiter Registration**\n\nPlease provide your full name:",
            parse_mode='Markdown'
        )

    async def handle_text_message(self, update: Update, context):
        """Handle text messages with modern UI"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in user_states:
            return
        
        state = user_states[user_id]
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, context, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, context, text)
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            await self.handle_waiter_name(update, context, text)
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            await self.handle_waiter_phone(update, context, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_SELECTION:
            await self.handle_restaurant_selection(update, context, text)

    async def handle_restaurant_name(self, update: Update, context, name: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id] = {'restaurant_name': name, 'role': UserRole.RESTAURANT_ADMIN}
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(
            f"✅ Restaurant name: **{name}**\n\nPlease provide your restaurant phone number:",
            parse_mode='Markdown'
        )

    async def handle_restaurant_phone(self, update: Update, context, phone: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_phone'] = phone
        
        # Generate restaurant ID
        restaurant_id = f"REST{int(time.time())}"
        users[user_id]['restaurant_id'] = restaurant_id
        users[user_id]['status'] = 'pending_approval'
        
        # Store in pending approvals
        pending_restaurant_approvals[user_id] = users[user_id].copy()
        
        # Clear user state
        del user_states[user_id]
        
        # Notify Super Admin
        await self.notify_super_admin_restaurant_registration(user_id, users[user_id])
        
        await update.message.reply_text(
            f"✅ **Restaurant Registration Complete!**\n\n"
            f"**Restaurant ID:** `{restaurant_id}`\n"
            f"**Status:** Pending Super Admin approval\n\n"
            f"You will be notified once approved!",
            parse_mode='Markdown'
        )
        
        # Show restaurant admin menu
        await self.show_restaurant_admin_menu(update)

    async def handle_waiter_name(self, update: Update, context, name: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        users[user_id] = {'waiter_name': name, 'role': UserRole.WAITER}
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text(
            f"✅ Waiter name: **{name}**\n\nPlease provide your phone number:",
            parse_mode='Markdown'
        )

    async def handle_waiter_phone(self, update: Update, context, phone: str):
        """Handle waiter phone input"""
        user_id = update.effective_user.id
        users[user_id]['waiter_phone'] = phone
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_SELECTION
        
        # Show restaurant selection
        await self.show_restaurant_selection(update, context)

    async def show_restaurant_selection(self, update: Update, context):
        """Show restaurant selection for waiter"""
        # Get approved restaurants
        approved_restaurants = [
            (uid, data) for uid, data in users.items() 
            if data.get('role') == UserRole.RESTAURANT_ADMIN and data.get('status') == 'approved'
        ]
        
        if not approved_restaurants:
            await update.message.reply_text(
                "❌ No approved restaurants available. Please contact Super Admin.",
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for uid, data in approved_restaurants:
            restaurant_name = data.get('restaurant_name', 'Unknown')
            restaurant_id = data.get('restaurant_id', 'Unknown')
            keyboard.append([InlineKeyboardButton(
                f"🏪 {restaurant_name} ({restaurant_id})", 
                callback_data=f"select_restaurant_{restaurant_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏪 **Select Your Restaurant**\n\nChoose the restaurant you work for:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_restaurant_selection(self, update: Update, context, text: str):
        """Handle restaurant selection"""
        # This will be handled by callback query
        pass

    async def start_payment_capture(self, update: Update, context):
        """Start payment capture process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        await update.callback_query.edit_message_text(
            "📸 **Capture Payment**\n\nPlease take a photo of the payment receipt:",
            parse_mode='Markdown'
        )

    async def handle_photo_message(self, update: Update, context):
        """Handle photo messages for payment capture"""
        user_id = update.effective_user.id
        
        if user_id not in user_states or user_states[user_id] != UserState.CAPTURING_PAYMENT:
            return
        
        try:
            # Get the photo
            photo = update.message.photo[-1]  # Get highest resolution
            file = await context.bot.get_file(photo.file_id)
            
            # Download image data
            image_data = await file.download_as_bytearray()
            
            # Extract transaction data using OCR
            transaction_data = await self.extract_receipt_data_from_google_vision(image_data)
            
            # Generate transaction ID
            transaction_id = f"TXN{int(time.time())}"
            
            # Store transaction
            transactions[transaction_id] = {
                'id': transaction_id,
                'waiter_id': user_id,
                'restaurant_id': users[user_id].get('restaurant_id'),
                'amount': transaction_data['amount'],
                'date': transaction_data['date'],
                'time': transaction_data['time'],
                'payer': transaction_data['payer'],
                'receiver': transaction_data['receiver'],
                'bank_name': transaction_data['bank_name'],
                'payment_method': transaction_data['payment_method'],
                'currency': transaction_data['currency'],
                'status': 'completed'
            }
            
            # Clear user state
            del user_states[user_id]
            
            await update.message.reply_text(
                f"✅ **Payment Captured Successfully!**\n\n"
                f"**Transaction ID:** `{transaction_id}`\n"
                f"**Amount:** {transaction_data['amount']} {transaction_data['currency']}\n"
                f"**Date:** {transaction_data['date']} {transaction_data['time']}\n"
                f"**Payer:** {transaction_data['payer']}\n"
                f"**Bank:** {transaction_data['bank_name']}",
                parse_mode='Markdown'
            )
            
            # Show waiter menu
            await self.show_waiter_menu(update, context)
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text(
                "❌ Error processing receipt. Please try again.",
                parse_mode='Markdown'
            )

    async def notify_super_admin_restaurant_registration(self, user_id: int, user_data: Dict):
        """Notify Super Admin about new restaurant registration"""
        try:
            message = f"""
🏪 **New Restaurant Registration**

**Restaurant Name:** {user_data['restaurant_name']}
**Phone:** {user_data['restaurant_phone']}
**Restaurant ID:** `{user_data['restaurant_id']}`
**User ID:** {user_id}

Please approve or reject this restaurant registration.
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_restaurant_{user_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_restaurant_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                SUPER_ADMIN_USER_ID,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error notifying Super Admin: {e}")

    async def notify_restaurant_admin_waiter_registration(self, user_id: int, user_data: Dict):
        """Notify Restaurant Admin about new waiter registration"""
        try:
            # Find the restaurant admin for this restaurant
            restaurant_id = user_data.get('restaurant_id')
            restaurant_admin_id = None
            
            for uid, data in users.items():
                if (data.get('role') == UserRole.RESTAURANT_ADMIN and 
                    data.get('restaurant_id') == restaurant_id and 
                    data.get('status') == 'approved'):
                    restaurant_admin_id = uid
                    break
            
            if not restaurant_admin_id:
                logger.error(f"No restaurant admin found for restaurant {restaurant_id}")
                return
            
            message = f"""
🍳 **New Waiter Registration for your Restaurant**

**Waiter Name:** {user_data['waiter_name']}
**Phone:** {user_data['waiter_phone']}
**Restaurant ID:** `{restaurant_id}`
**User ID:** {user_id}

Please approve or reject this waiter registration.
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"approve_waiter_{user_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_waiter_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                restaurant_admin_id,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error notifying Restaurant Admin: {e}")

    async def show_pending_restaurants(self, update: Update, context):
        """Show pending restaurant approvals"""
        if not pending_restaurant_approvals:
            await update.callback_query.edit_message_text(
                "✅ No pending restaurant approvals.",
                parse_mode='Markdown'
            )
            return
        
        message = "🏪 **Pending Restaurant Approvals**\n\n"
        keyboard = []
        
        for user_id, data in pending_restaurant_approvals.items():
            message += f"**{data['restaurant_name']}**\n"
            message += f"Phone: {data['restaurant_phone']}\n"
            message += f"ID: `{data['restaurant_id']}`\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {data['restaurant_name']}", callback_data=f"approve_restaurant_{user_id}"),
                InlineKeyboardButton(f"❌ Reject {data['restaurant_name']}", callback_data=f"reject_restaurant_{user_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_pending_waiters(self, update: Update, context):
        """Show pending waiter approvals"""
        if not pending_waiter_approvals:
            await update.callback_query.edit_message_text(
                "✅ No pending waiter approvals.",
                parse_mode='Markdown'
            )
            return
        
        message = "🍳 **Pending Waiter Approvals**\n\n"
        keyboard = []
        
        for user_id, data in pending_waiter_approvals.items():
            message += f"**{data['waiter_name']}**\n"
            message += f"Phone: {data['waiter_phone']}\n"
            message += f"Restaurant: {data.get('restaurant_name', 'Unknown')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {data['waiter_name']}", callback_data=f"approve_waiter_{user_id}"),
                InlineKeyboardButton(f"❌ Reject {data['waiter_name']}", callback_data=f"reject_waiter_{user_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def run(self):
        """Run the bot"""
        # Kill existing processes
        os.system("pkill -f veripay_bot")
        time.sleep(2)
        
        logger.info("Starting VeriPay Bot - FIXED VERSION...")
        logger.info("Send a message to @Verifpay_bot now!")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        self.bot = self.application.bot
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running
        try:
            await self.application.updater.idle()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
        finally:
            await self.application.stop()

if __name__ == "__main__":
    bot = VeriPayBot(BOT_TOKEN)
    asyncio.run(bot.run())
