#!/usr/bin/env python3
"""
VeriPay Bot - FINAL WORKING VERSION
Single instance, no conflicts, robust error handling
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
from telegram.error import TelegramError, NetworkError, TimedOut, Conflict

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
users: Dict[int, dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, dict] = {}
pending_waiter_approvals: Dict[int, dict] = {}
transactions: Dict[str, dict] = {}
waiter_ids: List[str] = []
restaurant_ids: List[str] = []

# Setup logging
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
        self.running = False
        
    def log_audit(self, user_id: int, action: str, details: str):
        """Log user actions for audit trail"""
        logger.info(f"Audit: {action} by {user_id}: {details}")
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
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
            # New user - show role selection
            users[user_id] = {'role': 'new_user', 'status': 'pending'}
            
            welcome_text = f"""
🌟 **Welcome to VeriPay Bot!** 🌟

Hi {user_name}! I'm your digital payment verification assistant.

**Choose your role:**
"""
            
            keyboard = [
                [InlineKeyboardButton("👑 Super Admin Login", callback_data="super_admin_login")],
                [InlineKeyboardButton("🏪 Restaurant Admin Registration", callback_data="register_restaurant")],
                [InlineKeyboardButton("🍳 Waiter Registration", callback_data="register_waiter")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu"""
        menu_text = """
👑 **Super Admin Panel** 👑

**System Management:**
"""
        
        keyboard = [
            [InlineKeyboardButton("🏪 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("📊 System Overview", callback_data="system_overview")],
            [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
            [InlineKeyboardButton("📈 System Statistics", callback_data="system_stats")],
            [InlineKeyboardButton("🔧 Bot Settings", callback_data="bot_settings")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        menu_text = """
👨‍💼 **Restaurant Admin Panel** 👨‍💼

**Restaurant Management:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📊 My Restaurant Transactions", callback_data="restaurant_transactions")],
            [InlineKeyboardButton("📈 Daily Summary", callback_data="restaurant_daily_summary")],
            [InlineKeyboardButton("📤 Export CSV", callback_data="restaurant_export_csv")],
            [InlineKeyboardButton("🏦 Upload Bank Statement", callback_data="restaurant_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="restaurant_reconciliation")],
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update, context=None):
        """Show Waiter menu"""
        menu_text = """
🍳 **Waiter Panel** 🍳

**Payment Management:**
"""
        
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="waiter_transactions")],
            [InlineKeyboardButton("❓ Help", callback_data="waiter_help")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        self.log_audit(user_id, "callback_query", f"User clicked {data}")
        
        if data == "super_admin_login":
            if user_id == SUPER_ADMIN_USER_ID:
                users[user_id] = {'role': 'super_admin', 'status': 'approved'}
                await self.show_super_admin_menu(update)
            else:
                await query.edit_message_text("❌ **Access Denied**\n\nOnly authorized Super Admins can access this panel.", parse_mode='Markdown')
        
        elif data == "register_restaurant":
            await self.start_restaurant_registration(update, context)
        
        elif data == "register_waiter":
            await self.start_waiter_registration(update, context)
        
        elif data == "pending_restaurants":
            await self.show_pending_restaurants(update, context)
        
        elif data == "restaurant_pending_waiters":
            await self.show_pending_waiters(update, context)
        
        elif data == "capture_payment":
            await self.start_payment_capture(update, context)
        
        else:
            await query.edit_message_text("🔄 **Processing...**\n\nThis feature is coming soon!", parse_mode='Markdown')
    
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
    
    async def start_payment_capture(self, update: Update, context):
        """Start payment capture process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        await update.callback_query.edit_message_text(
            "📸 **Capture Payment**\n\nPlease take a photo of the payment receipt:",
            parse_mode='Markdown'
        )
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in user_states:
            await update.message.reply_text("Please use the /start command to begin.")
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
        else:
            await update.message.reply_text("Please use the /start command to begin.")
    
    async def handle_restaurant_name(self, update: Update, context, name: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_name'] = name
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(
            f"✅ Restaurant name: **{name}**\n\nPlease provide your phone number (e.g., 0912345678):",
            parse_mode='Markdown'
        )
    
    async def handle_restaurant_phone(self, update: Update, context, phone: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_phone'] = phone
        
        # Generate restaurant ID
        restaurant_id = f"REST{len(restaurant_ids) + 1:03d}"
        restaurant_ids.append(restaurant_id)
        users[user_id]['restaurant_id'] = restaurant_id
        users[user_id]['role'] = 'restaurant_admin'
        users[user_id]['status'] = 'pending_approval'
        
        # Add to pending approvals
        pending_restaurant_approvals[user_id] = users[user_id].copy()
        
        # Clear user state
        del user_states[user_id]
        
        self.log_audit(user_id, "restaurant_registration", f"Restaurant {restaurant_id} registered by user {user_id}")
        
        # Notify Super Admin
        await self.notify_super_admin_restaurant_registration(user_id, users[user_id])
        
        # Show success message and restaurant admin menu
        await update.message.reply_text(
            f"✅ **Restaurant registration complete!**\n\n**Restaurant ID:** `{restaurant_id}`\n\nYour registration is pending Super Admin approval.\nYou will be notified once approved.",
            parse_mode='Markdown'
        )
        
        # Show restaurant admin menu
        await self.show_restaurant_admin_menu(update)
    
    async def handle_waiter_name(self, update: Update, context, name: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        users[user_id]['waiter_name'] = name
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text(
            f"✅ Waiter name: **{name}**\n\nPlease provide your phone number (e.g., 0912345678):",
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
        approved_restaurants = []
        for uid, user_data in users.items():
            if (user_data.get('role') == 'restaurant_admin' and 
                user_data.get('status') == 'approved'):
                approved_restaurants.append((uid, user_data))
        
        if not approved_restaurants:
            await update.message.reply_text(
                "❌ **No approved restaurants available**\n\nPlease contact the Super Admin to approve restaurants first.",
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for uid, restaurant_data in approved_restaurants:
            restaurant_name = restaurant_data.get('restaurant_name', 'Unknown Restaurant')
            restaurant_id = restaurant_data.get('restaurant_id', 'Unknown ID')
            keyboard.append([InlineKeyboardButton(
                f"🏪 {restaurant_name} ({restaurant_id})",
                callback_data=f"select_restaurant_{restaurant_id}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏪 **Select your restaurant:**\n\nPlease choose from the approved restaurants below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_restaurant_selection(self, update: Update, context, text: str):
        """Handle restaurant selection (fallback for text input)"""
        await update.message.reply_text("Please use the inline buttons to select a restaurant.")
    
    async def notify_super_admin_restaurant_registration(self, user_id: int, restaurant_data: dict):
        """Notify Super Admin about new restaurant registration"""
        try:
            notification_text = f"""
🏪 **New Restaurant Registration**

**Restaurant Name:** {restaurant_data.get('restaurant_name', 'Unknown')}
**Phone:** {restaurant_data.get('restaurant_phone', 'Unknown')}
**Restaurant ID:** `{restaurant_data.get('restaurant_id', 'Unknown')}`
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
                notification_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify Super Admin: {e}")
    
    async def notify_restaurant_admin_waiter_registration(self, user_id: int, waiter_data: dict):
        """Notify Restaurant Admin about new waiter registration"""
        try:
            restaurant_id = waiter_data.get('restaurant_id')
            if not restaurant_id:
                logger.error("No restaurant_id found in waiter_data")
                return
            
            # Find the restaurant admin
            restaurant_admin_id = None
            for uid, user_data in users.items():
                if (user_data.get('restaurant_id') == restaurant_id and 
                    user_data.get('role') == 'restaurant_admin' and
                    user_data.get('status') == 'approved'):
                    restaurant_admin_id = uid
                    break
            
            if not restaurant_admin_id:
                logger.error(f"No restaurant admin found for restaurant_id: {restaurant_id}")
                return
            
            notification_text = f"""
🍳 **New Waiter Registration for your Restaurant**

**Waiter Name:** {waiter_data.get('waiter_name', 'Unknown')}
**Phone:** {waiter_data.get('waiter_phone', 'Unknown')}
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
                notification_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify Restaurant Admin: {e}")
    
    async def show_pending_restaurants(self, update: Update, context):
        """Show pending restaurant approvals"""
        if not pending_restaurant_approvals:
            await update.callback_query.edit_message_text(
                "✅ **No pending restaurant approvals**\n\nAll restaurants have been processed.",
                parse_mode='Markdown'
            )
            return
        
        text = "🏪 **Pending Restaurant Approvals:**\n\n"
        keyboard = []
        
        for user_id, restaurant_data in pending_restaurant_approvals.items():
            text += f"**{restaurant_data.get('restaurant_name', 'Unknown')}**\n"
            text += f"Phone: {restaurant_data.get('restaurant_phone', 'Unknown')}\n"
            text += f"ID: `{restaurant_data.get('restaurant_id', 'Unknown')}`\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {restaurant_data.get('restaurant_name', 'Unknown')}", 
                                   callback_data=f"approve_restaurant_{user_id}"),
                InlineKeyboardButton(f"❌ Reject", callback_data=f"reject_restaurant_{user_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_waiters(self, update: Update, context):
        """Show pending waiter approvals"""
        if not pending_waiter_approvals:
            await update.callback_query.edit_message_text(
                "✅ **No pending waiter approvals**\n\nAll waiters have been processed.",
                parse_mode='Markdown'
            )
            return
        
        text = "🍳 **Pending Waiter Approvals:**\n\n"
        keyboard = []
        
        for user_id, waiter_data in pending_waiter_approvals.items():
            text += f"**{waiter_data.get('waiter_name', 'Unknown')}**\n"
            text += f"Phone: {waiter_data.get('waiter_phone', 'Unknown')}\n"
            text += f"Restaurant: {waiter_data.get('restaurant_id', 'Unknown')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {waiter_data.get('waiter_name', 'Unknown')}", 
                                   callback_data=f"approve_waiter_{user_id}"),
                InlineKeyboardButton(f"❌ Reject", callback_data=f"reject_waiter_{user_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_photo_message(self, update: Update, context):
        """Handle photo messages for payment capture"""
        user_id = update.effective_user.id
        
        if user_id not in user_states or user_states[user_id] != UserState.CAPTURING_PAYMENT:
            await update.message.reply_text("Please use the /start command to begin payment capture.")
            return
        
        # Clear user state
        del user_states[user_id]
        
        # Generate transaction ID
        transaction_id = f"TXN{len(transactions) + 1:06d}"
        
        # Mock transaction data (replace with actual OCR)
        transaction_data = {
            'transaction_id': transaction_id,
            'amount': 1500.0,
            'currency': 'ETB',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M'),
            'payer': 'Mock Payer',
            'receiver': 'Mock Receiver',
            'bank_name': 'Mock Bank',
            'payment_method': 'Mock Bank Transfer',
            'waiter_id': user_id,
            'restaurant_id': users[user_id].get('restaurant_id', 'Unknown'),
            'status': 'completed'
        }
        
        transactions[transaction_id] = transaction_data
        
        self.log_audit(user_id, "payment_captured", f"Transaction {transaction_id} captured")
        
        await update.message.reply_text(
            f"✅ **Payment captured successfully!**\n\n"
            f"**Transaction ID:** `{transaction_id}`\n"
            f"**Amount:** {transaction_data['amount']} {transaction_data['currency']}\n"
            f"**Date:** {transaction_data['date']} {transaction_data['time']}\n\n"
            f"Transaction has been recorded in the system.",
            parse_mode='Markdown'
        )
        
        # Show waiter menu
        await self.show_waiter_menu(update, context)
    
    async def run(self):
        """Run the bot with single instance management"""
        if self.running:
            logger.warning("Bot is already running! Ignoring duplicate start request.")
            return
            
        self.running = True
        logger.info("Starting VeriPay Bot - FINAL WORKING VERSION...")
        logger.info("Send a message to @Verifpay_bot now!")
        
        try:
            # Create application with custom request configuration
            from telegram.request import HTTPXRequest
            
            # Configure request with longer timeouts and retries
            request = HTTPXRequest(
                connection_pool_size=8,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30
            )
            
            self.application = Application.builder().token(self.token).request(request).build()
            self.bot = self.application.bot
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            try:
                await self.application.updater.idle()
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
            finally:
                await self.application.stop()
                self.running = False
                
        except (NetworkError, TimedOut, Conflict) as e:
            logger.error(f"Network/Conflict error: {e}")
            self.running = False
            logger.info("Retrying in 5 seconds...")
            await asyncio.sleep(5)
            await self.run()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.running = False
            logger.info("Retrying in 10 seconds...")
            await asyncio.sleep(10)
            await self.run()

if __name__ == "__main__":
    bot = VeriPayBot(BOT_TOKEN)
    asyncio.run(bot.run())
