#!/usr/bin/env python3
"""
VeriPay Bot - Fixed Super Admin Approvals
Only fixes the approval buttons issue without breaking anything else
"""

import asyncio
import logging
import re
import base64
import io
import random
from datetime import datetime
try:
    import pytesseract
    from PIL import Image, ImageOps
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False    OCR_AVAILABLE = False

    VISION_AVAILABLE = True
except Exception:
    VISION_AVAILABLE = False
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
    WAITING_FOR_RECEIPT = "waiting_for_receipt"

# Global data storage
users: Dict[int, Dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, Dict] = {}
pending_waiter_approvals: Dict[int, Dict] = {}
restaurant_ids: Dict[int, str] = {}
waiter_ids: Dict[int, str] = {}
transactions: List[Dict] = []

# Super Admin ID
SUPER_ADMIN_ID = 369249230

class VeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.bot = self.application.bot
        self.setup_handlers()
        
        # Initialize super admin
        users[SUPER_ADMIN_ID] = {
            "role": UserRole.SUPER_ADMIN,
            "state": UserState.IDLE,
            "name": "Super Admin"
        }

    def setup_handlers(self):
        """Setup all command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.first_name or "User"
        
        logger.info(f"Audit: start_command by {user_id}: User {username} started bot")
        
        if user_id not in users:
            users[user_id] = {
                "role": UserRole.NEW_USER,
                "state": UserState.IDLE,
                "name": username
            }
            user_states[user_id] = UserState.IDLE

        user = users[user_id]
        
        if user["role"] == UserRole.SUPER_ADMIN:
            await self.show_super_admin_menu(update, None)
        elif user["role"] == UserRole.RESTAURANT_ADMIN:
            await self.show_restaurant_admin_menu(update)
        elif user["role"] == UserRole.WAITER:
            await self.show_waiter_menu(update)
        else:
            await self.show_role_selection(update)

    async def show_role_selection(self, update: Update):
        """Show role selection menu for new users"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🤖 **Welcome to VeriPay Bot!**\n\nPlease select your role:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu with approval buttons"""
        keyboard = [
            [InlineKeyboardButton("📋 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("🏪 Active Restaurants", callback_data="active_restaurants")],
            [InlineKeyboardButton("📊 Daily Reports", callback_data="daily_reports")],
            [InlineKeyboardButton("❓ Admin Help", callback_data="admin_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "👑 **Super Admin Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("📊 All Transactions", callback_data="all_transactions")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
            [InlineKeyboardButton("📈 Download Today's Report", callback_data="download_report")],
            [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🏪 **Restaurant Admin Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("❓ Help", callback_data="waiter_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "👨‍💼 **Waiter Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "register_restaurant":
            await self.start_restaurant_registration(query)
        elif data == "register_waiter":
            await self.start_waiter_registration(query)
        elif data == "pending_restaurants":
            await self.show_pending_restaurants(query)
        elif data == "active_restaurants":
            await self.show_active_restaurants(query)
        elif data == "daily_reports":
            await self.show_daily_reports(query)
        elif data == "admin_help":
            await self.show_admin_help(query)
        elif data == "all_transactions":
            await self.show_all_transactions(query)
        elif data == "manage_waiters":
            await self.show_manage_waiters(query)
        elif data == "restaurant_settings":
            await self.show_restaurant_settings(query)
        elif data == "download_report":
            await self.download_report(query)
        elif data == "make_reconciliation":
            await self.show_reconciliation_options(query)
        elif data == "capture_payment":
            await self.start_capture_payment(query)
        elif data == "my_transactions":
            await self.show_my_transactions(query)
        elif data == "waiter_settings":
            await self.show_waiter_settings(query)
        elif data == "waiter_help":
            await self.show_waiter_help(query)
        elif data == "back_to_super_admin_menu":
            await self.show_super_admin_menu_callback(query)
        elif data == "back_to_restaurant_admin_menu":
            await self.show_restaurant_admin_menu_callback(query)
        elif data == "back_to_waiter_menu":
            await self.show_waiter_menu_callback(query)
        elif data.startswith("approve_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.approve_restaurant(query, restaurant_user_id)
        elif data.startswith("reject_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.reject_restaurant(query, restaurant_user_id)
        elif data.startswith("approve_waiter_"):
            waiter_user_id = int(data.split("_")[2])
            await self.approve_waiter(query, waiter_user_id)
        elif data.startswith("reject_waiter_"):
            waiter_user_id = int(data.split("_")[2])
            await self.reject_waiter(query, waiter_user_id)
        elif data == "sign_out":
            await self.sign_out(query)

    async def show_pending_restaurants(self, query):
        """Show pending restaurant approvals with approve/reject buttons"""
        if not pending_restaurant_approvals:
            message = "📋 **Pending Restaurant Approvals**\n\nNo pending approvals at the moment."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        else:
            message = "📋 **Pending Restaurant Approvals**\n\n"
            keyboard = []
            
            for user_id, data in pending_restaurant_approvals.items():
                message += f"🏪 **{data['restaurant_name']}**\n"
                message += f"📞 Phone: {data['restaurant_phone']}\n"
                message += f"👤 Owner: {data['owner_name']}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {data['restaurant_name']}", callback_data=f"approve_restaurant_{user_id}"),
                    InlineKeyboardButton(f"❌ Reject {data['restaurant_name']}", callback_data=f"reject_restaurant_{user_id}")
                ])
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")])
        
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
            
            # Confirm to approver
            message = f"✅ **Restaurant Approved**\n\n{data['restaurant_name']} has been approved and is now active."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Auto-open Restaurant Admin menu for the approved user
            ra_keyboard = [
                [InlineKeyboardButton("📊 All Transactions", callback_data="all_transactions")],
                [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
                [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
                [InlineKeyboardButton("📈 Download Today's Report", callback_data="download_report")],
                [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
                [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
            ]
            ra_markup = InlineKeyboardMarkup(ra_keyboard)
            ra_message = "🏪 **Restaurant Admin Dashboard**\n\nSelect an option:"
try:
    import pytesseract
    from PIL import Image, ImageOps
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False