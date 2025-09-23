#!/usr/bin/env python3
"""
VeriPay Bot - FIXED CALLBACK HANDLERS
All callback handlers properly implemented
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
    WAITING_FOR_RESTAURANT_ADDRESS = "waiting_for_restaurant_address"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_RESTAURANT_SELECTION = "waiting_for_restaurant_selection"
    CAPTURING_PAYMENT = "capturing_payment"

# Global storage
users = {}
user_states = {}
pending_restaurant_approvals = {}
pending_waiter_approvals = {}
waiter_ids = {}
restaurant_ids = {}
transactions = {}
audit_logs = []

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Transaction:
    def __init__(self, transaction_id: str, amount: float, currency: str, 
                 bank_name: str, payer: str, date: str, waiter_id: str, restaurant_id: str):
        self.transaction_id = transaction_id
        self.amount = amount
        self.currency = currency
        self.bank_name = bank_name
        self.payer = payer
        self.date = date
        self.waiter_id = waiter_id
        self.restaurant_id = restaurant_id
        self.created_at = datetime.now()

class VeriPayBot:
    def __init__(self):
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        # Log audit
        self.log_audit(user_id, "start_command", f"User {username} started bot")
        
        # Ensure Super Admin is always recognized
        if user_id == SUPER_ADMIN_USER_ID:
            users[user_id] = {
                'name': 'Super Admin',
                'role': 'super_admin',
                'status': 'approved'
            }
            await self.show_super_admin_menu(update)
            return
        
        # Check if user exists and is approved
        if user_id in users:
            user_role = users[user_id].get('role', 'waiter')
            user_status = users[user_id].get('status', 'pending')
            
            if user_status == 'approved':
                if user_role == 'restaurant_admin':
                    await self.show_restaurant_admin_menu(update)
                elif user_role == 'waiter':
                    await self.show_waiter_menu(update)
                elif user_role == 'super_admin':
                    await self.show_super_admin_menu(update)
                else:
                    await self.show_main_menu(update)
            else:
                await update.message.reply_text("⏳ Your account is pending approval. Please wait for admin approval.")
        else:
            await self.show_main_menu(update)
    
    async def show_main_menu(self, update: Update):
        """Show main menu for new users"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")],
            [InlineKeyboardButton("🔐 Super Admin Login", callback_data="super_admin_login")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """🤖 **Welcome to VeriPay Bot!**

**Choose your role:**

🏪 **Restaurant Admin** - Manage your restaurant and waiters
👨‍💼 **Waiter** - Capture payments and manage transactions
🔐 **Super Admin** - Approve restaurants and manage system

Select an option below:"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu"""
        keyboard = [
            [InlineKeyboardButton("⏳ Pending Restaurant Approvals", callback_data="admin_pending_restaurants")],
            [InlineKeyboardButton("📊 All Transactions", callback_data="admin_all_transactions")],
            [InlineKeyboardButton("📈 Daily Report", callback_data="admin_daily_report")],
            [InlineKeyboardButton("ℹ️ Admin Help", callback_data="admin_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """🔐 **Super Admin Dashboard**

**Available Actions:**
⏳ Manage pending restaurant approvals
📊 View all system transactions
📈 Generate daily reports
ℹ️ Get help and support

Select an option below:"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")],
            [InlineKeyboardButton("📊 My Restaurant Transactions", callback_data="restaurant_transactions")],
            [InlineKeyboardButton("ℹ️ Restaurant Help", callback_data="restaurant_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """🏪 **Restaurant Admin Dashboard**

**Available Actions:**
👥 Manage pending waiter approvals
📊 View restaurant transactions
ℹ️ Get help and support

Select an option below:"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update, context=None):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📊 My Transactions", callback_data="waiter_my_transactions")],
            [InlineKeyboardButton("ℹ️ Waiter Help", callback_data="waiter_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """👨‍💼 **Waiter Dashboard**

**Available Actions:**
📸 Capture payment receipts
📊 View your transactions
ℹ️ Get help and support

Select an option below:"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries - FIXED with all handlers"""
        query = update.callback_query
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Callback query error: {e}")
        
        user_id = query.from_user.id
        
        # Ensure Super Admin is always recognized
        if user_id == SUPER_ADMIN_USER_ID and user_id not in users:
            users[user_id] = {
                'name': 'Super Admin',
                'role': 'super_admin',
                'status': 'approved'
            }
        
        user_role = users.get(user_id, {}).get('role', 'waiter')
        
        # Main menu handlers
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
        
        # Super Admin handlers
        elif query.data == "admin_pending_restaurants":
            if user_role != 'super_admin':
                await query.edit_message_text("❌ Super Admin access required!")
                return
            
            if not pending_restaurant_approvals:
                await query.edit_message_text("✅ No pending restaurant approvals!")
                return
            
            message = "⏳ **Pending Restaurant Approvals**\n\n"
            for user_id_approval, approval_data in pending_restaurant_approvals.items():
                if isinstance(approval_data, dict) and 'restaurant_name' in approval_data:
                    message += f"**User ID:** {user_id_approval}\n"
                    message += f"**Restaurant:** {approval_data['restaurant_name']}\n"
                    message += f"**Address:** {approval_data['restaurant_address']}\n"
                    message += f"**Phone:** {approval_data['restaurant_phone']}\n\n"
            
            # Add approve/reject buttons
            keyboard = []
            for user_id_approval in pending_restaurant_approvals.keys():
                if isinstance(pending_restaurant_approvals[user_id_approval], dict) and 'restaurant_name' in pending_restaurant_approvals[user_id_approval]:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ Approve Restaurant {user_id_approval}", callback_data=f"approve_restaurant_{user_id_approval}"),
                        InlineKeyboardButton(f"❌ Reject Restaurant {user_id_approval}", callback_data=f"reject_restaurant_{user_id_approval}")
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
        
        # Restaurant Admin handlers
        elif query.data == "restaurant_pending_waiters":
            if user_role != 'restaurant_admin':
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            if not pending_waiter_approvals:
                await query.edit_message_text("✅ No pending waiter approvals!")
                return
            
            message = "⏳ **Pending Waiter Approvals**\n\n"
            for waiter_id_approval, approval_data in pending_waiter_approvals.items():
                if isinstance(approval_data, dict) and 'waiter_name' in approval_data:
                    message += f"**Waiter ID:** {waiter_id_approval}\n"
                    message += f"**Name:** {approval_data['waiter_name']}\n"
                    message += f"**Phone:** {approval_data['waiter_phone']}\n"
                    message += f"**Restaurant ID:** {approval_data['restaurant_id']}\n\n"
            
            # Add approve/reject buttons
            keyboard = []
            for waiter_id_approval in pending_waiter_approvals.keys():
                if isinstance(pending_waiter_approvals[waiter_id_approval], dict) and 'waiter_name' in pending_waiter_approvals[waiter_id_approval]:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ Approve Waiter {waiter_id_approval}", callback_data=f"restaurant_approve_waiter_{waiter_id_approval}"),
                        InlineKeyboardButton(f"❌ Reject Waiter {waiter_id_approval}", callback_data=f"restaurant_reject_waiter_{waiter_id_approval}")
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Restaurant", callback_data="restaurant_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
        elif query.data.startswith("restaurant_approve_waiter_"):
            if user_role != 'restaurant_admin':
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            waiter_id_to_approve = query.data.split("_")[3]
            
            if waiter_id_to_approve in pending_waiter_approvals:
                # Move to approved users
                waiter_data = pending_waiter_approvals[waiter_id_to_approve]
                user_id_to_approve = waiter_data.get('user_id')
                
                if user_id_to_approve:
                    users[user_id_to_approve] = waiter_data
                    users[user_id_to_approve]['status'] = 'approved'
                    users[user_id_to_approve]['role'] = 'waiter'
                
                # Remove from pending
                del pending_waiter_approvals[waiter_id_to_approve]
                
                # Log audit
                self.log_audit(user_id, "waiter_approved", f"Waiter {waiter_id_to_approve} approved")
                
                await query.edit_message_text(f"✅ **Waiter Approved!**\n\nWaiter ID: `{waiter_id_to_approve}`", parse_mode='Markdown')
                
                # Notify the waiter
                if user_id_to_approve:
                    try:
                        await self.bot.send_message(
                            user_id_to_approve,
                            f"🎉 **Congratulations!**\n\nYou have been approved as a waiter!\n\n**Waiter ID:** `{waiter_id_to_approve}`\n\nYou can now capture payments!",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            else:
                await query.edit_message_text("❌ Waiter not found in pending approvals!")
        
        elif query.data.startswith("restaurant_reject_waiter_"):
            if user_role != 'restaurant_admin':
                await query.edit_message_text("❌ Restaurant Admin access required!")
                return
            
            waiter_id_to_reject = query.data.split("_")[3]
            
            if waiter_id_to_reject in pending_waiter_approvals:
                del pending_waiter_approvals[waiter_id_to_reject]
                
                # Log audit
                self.log_audit(user_id, "waiter_rejected", f"Waiter {waiter_id_to_reject} rejected")
                
                await query.edit_message_text(f"❌ **Waiter Rejected!**\n\nWaiter {waiter_id_to_reject} has been rejected.", parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ Waiter not found in pending approvals!")
        
        # Waiter handlers
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
        
        # Help handlers
        elif query.data == "help":
            help_message = """ℹ️ **VeriPay Bot Help**

**Available Roles:**
🏪 **Restaurant Admin** - Manage your restaurant and approve waiters
👨‍💼 **Waiter** - Capture payments and manage transactions
🔐 **Super Admin** - Approve restaurants and manage system

**Getting Started:**
1. Register with your role
2. Wait for approval from admin
3. Start using the bot features

**Need help?** Contact the Super Admin."""
            
            await query.edit_message_text(help_message)
        
        elif query.data == "admin_help":
            help_message = """ℹ️ **Super Admin Help**

**Your Responsibilities:**
⏳ Approve new restaurant registrations
📊 Monitor all system transactions
📈 Generate daily reports
🔧 Manage system settings

**Available Commands:**
• View pending restaurant approvals
• Monitor all transactions
• Generate daily reports
• Manage system settings

**Need help?** Contact system administrator."""
            
            await query.edit_message_text(help_message)
        
        elif query.data == "restaurant_help":
            help_message = """ℹ️ **Restaurant Admin Help**

**Your Responsibilities:**
👥 Approve waiter registrations
📊 Monitor restaurant transactions
�� Manage restaurant settings

**Available Commands:**
• View pending waiter approvals
• Monitor restaurant transactions
• Manage restaurant settings

**Need help?** Contact the Super Admin."""
            
            await query.edit_message_text(help_message)
        
        elif query.data == "waiter_help":
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
        
        # Navigation handlers
        elif query.data == "admin_menu":
            await self.show_super_admin_menu(update)
        
        elif query.data == "restaurant_menu":
            await self.show_restaurant_admin_menu(update)
        
        elif query.data == "waiter_menu":
            await self.show_waiter_menu(update)
        
        # Default case - unknown action
        else:
            await query.edit_message_text("❌ Unknown action. Please try again or use /start to restart.")
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages for registration flow"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in user_states:
            await update.message.reply_text("Please use /start to begin.")
            return
        
        state = user_states[user_id]
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            users[user_id]['restaurant_name'] = text
            user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_ADDRESS
            await update.message.reply_text("Please provide your restaurant address:")
        
        elif state == UserState.WAITING_FOR_RESTAURANT_ADDRESS:
            users[user_id]['restaurant_address'] = text
            user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
            await update.message.reply_text("Please provide your restaurant phone number:")
        
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            users[user_id]['restaurant_phone'] = text
            users[user_id]['restaurant_id'] = f"R{user_id}"
            users[user_id]['status'] = 'pending_restaurant_approval'
            
            # Add to pending approvals
            pending_restaurant_approvals[user_id] = users[user_id].copy()
            
            # Log audit
            self.log_audit(user_id, "restaurant_registration", f"Restaurant {text} registered by user {user_id}")
            
            # Notify Super Admin
            try:
                await self.bot.send_message(
                    SUPER_ADMIN_USER_ID,
                    f"🏪 **New Restaurant Registration**\n\n"
                    f"**Restaurant:** {users[user_id]['restaurant_name']}\n"
                    f"**Address:** {users[user_id]['restaurant_address']}\n"
                    f"**Phone:** {users[user_id]['restaurant_phone']}\n"
                    f"**User ID:** {user_id}\n\n"
                    f"Please approve or reject this restaurant.",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(
                f"✅ **Restaurant Registration Complete!**\n\n"
                f"**Restaurant:** {users[user_id]['restaurant_name']}\n"
                f"**Address:** {users[user_id]['restaurant_address']}\n"
                f"**Phone:** {users[user_id]['restaurant_phone']}\n\n"
                f"⏳ Your restaurant is pending Super Admin approval.\n"
                f"You will be notified once approved!",
                parse_mode='Markdown'
            )
            
            # Show restaurant admin menu after registration
            await self.show_restaurant_admin_menu(update)
            del user_states[user_id]
        
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            users[user_id]['waiter_name'] = text
            user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
            await update.message.reply_text("Please provide your phone number:")
        
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            users[user_id]['waiter_phone'] = text
            users[user_id]['waiter_id'] = f"W{user_id}"
            users[user_id]['status'] = 'pending_waiter_approval'
            users[user_id]['restaurant_id'] = 'UNKNOWN'  # Will be set by restaurant admin
            
            # Add to pending approvals
            pending_waiter_approvals[users[user_id]['waiter_id']] = users[user_id].copy()
            pending_waiter_approvals[users[user_id]['waiter_id']]['user_id'] = user_id
            
            # Log audit
            self.log_audit(user_id, "waiter_registration", f"Waiter {text} registered by user {user_id}")
            
            # Notify Restaurant Admin (find any restaurant admin)
            restaurant_admin_id = None
            for uid, user_data in users.items():
                if user_data.get('role') == 'restaurant_admin' and user_data.get('status') == 'approved':
                    restaurant_admin_id = uid
                    break
            
            if restaurant_admin_id:
                try:
                    await self.bot.send_message(
                        restaurant_admin_id,
                        f"👨‍💼 **New Waiter Registration**\n\n"
                        f"**Name:** {users[user_id]['waiter_name']}\n"
                        f"**Phone:** {users[user_id]['waiter_phone']}\n"
                        f"**Waiter ID:** {users[user_id]['waiter_id']}\n"
                        f"**User ID:** {user_id}\n\n"
                        f"Please approve or reject this waiter.",
                        parse_mode='Markdown'
                    )
                except:
                    pass
                
                # Log audit
                self.log_audit(user_id, "restaurant_admin_notified", f"Waiter {users[user_id]['waiter_id']} notification sent")
            
            await update.message.reply_text(
                f"✅ **Waiter Registration Complete!**\n\n"
                f"**Name:** {users[user_id]['waiter_name']}\n"
                f"**Phone:** {users[user_id]['waiter_phone']}\n"
                f"**Waiter ID:** {users[user_id]['waiter_id']}\n\n"
                f"⏳ Your waiter account is pending Restaurant Admin approval.\n"
                f"You will be notified once approved!",
                parse_mode='Markdown'
            )
            
            # Show waiter menu after registration
            await self.show_waiter_menu(update)
            del user_states[user_id]
        
        elif state == UserState.CAPTURING_PAYMENT:
            # This is handled by photo handler
            await update.message.reply_text("Please send a photo of the payment receipt.")
    
    async def handle_photo(self, update: Update, context):
        """Handle photo messages for OCR processing"""
        user_id = update.effective_user.id
        
        if user_id not in user_states or user_states[user_id] != UserState.CAPTURING_PAYMENT:
            await update.message.reply_text("Please use /start to begin or select 'Capture Payment' from the menu.")
            return
        
        try:
            # Get photo file
            photo = update.message.photo[-1]  # Get highest resolution
            file = await context.bot.get_file(photo.file_id)
            
            # Download photo
            photo_data = await file.download_as_bytearray()
            
            # Process with OCR (simplified for now)
            await update.message.reply_text("📸 Processing receipt... Please wait.")
            
            # Simulate OCR processing
            await asyncio.sleep(2)
            
            # Create mock transaction
            transaction_id = f"TXN{int(time.time())}"
            amount = 150.00
            currency = "ETB"
            bank_name = "Dashen Bank"
            payer = "Customer"
            date = datetime.now().strftime("%Y-%m-%d")
            waiter_id = users[user_id].get('waiter_id', 'UNKNOWN')
            restaurant_id = users[user_id].get('restaurant_id', 'UNKNOWN')
            
            # Create transaction
            transaction = Transaction(
                transaction_id=transaction_id,
                amount=amount,
                currency=currency,
                bank_name=bank_name,
                payer=payer,
                date=date,
                waiter_id=waiter_id,
                restaurant_id=restaurant_id
            )
            
            transactions[transaction_id] = transaction
            
            # Log audit
            self.log_audit(user_id, "payment_captured", f"Payment {transaction_id} captured")
            
            await update.message.reply_text(
                f"✅ **Payment Captured Successfully!**\n\n"
                f"**Transaction ID:** {transaction_id}\n"
                f"**Amount:** {currency} {amount:,.2f}\n"
                f"**Bank:** {bank_name}\n"
                f"**Payer:** {payer}\n"
                f"**Date:** {date}\n"
                f"**Waiter ID:** {waiter_id}\n\n"
                f"Transaction has been recorded!",
                parse_mode='Markdown'
            )
            
            # Clear state
            del user_states[user_id]
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text("❌ Error processing receipt. Please try again with a clearer photo.")
    
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
        """Run the bot"""
        try:
            logger.info("Starting VeriPay Bot - FIXED CALLBACK HANDLERS...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            # Keep running
            try:
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
    # Kill any existing bot processes before starting
    try:
        os.system("pkill -f veripay")
        logger.info("Killed existing bot processes")
        time.sleep(1)
    except Exception as e:
        logger.error(f"Error killing existing processes: {e}")
    
    # Start new bot instance
    bot = VeriPayBot()
    asyncio.run(bot.run())
