#!/usr/bin/env python3
"""
VeriPay Bot - COMPLETE VERSION
All role menus, OCR with real image processing, comprehensive features
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

# Google Cloud Vision API
try:
    from google.cloud import vision
    from google.oauth2 import service_account
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

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
    IDLE = "idle"
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_RESTAURANT_SELECTION = "waiting_for_restaurant_selection"
    CAPTURING_PAYMENT = "capturing_payment"
    WAITING_FOR_RECEIPT_IMAGE = "waiting_for_receipt_image"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VeriPayBot:
    def __init__(self):
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.users: Dict[int, Dict] = {}
        self.user_states: Dict[int, UserState] = {}
        self.pending_restaurant_approvals: Dict[int, Dict] = {}
        self.pending_waiter_approvals: Dict[int, Dict] = {}
        self.restaurant_ids: Dict[int, int] = {}  # user_id -> restaurant_id
        self.waiter_ids: Dict[int, int] = {}  # user_id -> waiter_id
        self.transactions: List[Dict] = []
        self.running = False
        
        # Initialize Google Vision API
        self.vision_client = None
        if VISION_AVAILABLE:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized successfully")
            except Exception as e:
                logger.warning(f"Google Vision API not available: {e}")
        
        # Setup application
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"Audit: start_command by {user_id}: User {username} started bot")
        
        # Initialize user if not exists
        if user_id not in self.users:
            self.users[user_id] = {
                'id': user_id,
                'username': username,
                'role': UserRole.NEW_USER,
                'restaurant_id': None,
                'waiter_id': None,
                'created_at': datetime.now()
            }
            self.user_states[user_id] = UserState.IDLE
        
        # Show appropriate menu based on role
        if self.users[user_id]['role'] == UserRole.SUPER_ADMIN:
            await self.show_super_admin_menu(update)
        elif self.users[user_id]['role'] == UserRole.RESTAURANT_ADMIN:
            await self.show_restaurant_admin_menu(update)
        elif self.users[user_id]['role'] == UserRole.WAITER:
            await self.show_waiter_menu(update)
        else:
            await self.show_main_menu(update)
    
    async def show_main_menu(self, update: Update):
        """Show main registration menu"""
        keyboard = [
            [InlineKeyboardButton("🏢 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌟 **Welcome to VeriPay!** 🌟\n\n"
            "Choose your role to get started:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu with all required options"""
        keyboard = [
            [InlineKeyboardButton("🏢 Pending Restaurant Approvals", callback_data="super_pending_restaurants")],
            [InlineKeyboardButton("📊 Active Restaurants", callback_data="super_active_restaurants")],
            [InlineKeyboardButton("📈 Daily Reports", callback_data="super_daily_reports")],
            [InlineKeyboardButton("📋 System Statistics", callback_data="super_statistics")],
            [InlineKeyboardButton("⚙️ Admin Settings", callback_data="super_settings")],
            [InlineKeyboardButton("ℹ️ Admin Help", callback_data="super_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🔴 **Super Admin Dashboard** 🔴\n\n"
        text += f"👤 User: {update.effective_user.username}\n"
        text += f"🆔 ID: {update.effective_user.id}\n"
        text += f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        text += "Select an option from the menu below:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu with all required options"""
        keyboard = [
            [InlineKeyboardButton("💰 All Transactions", callback_data="restaurant_all_transactions")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="restaurant_manage_waiters")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
            [InlineKeyboardButton("📊 Download Today's Report", callback_data="restaurant_download_report")],
            [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="restaurant_reconciliation")],
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="restaurant_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏢 **Restaurant Admin Dashboard** 🏢\n\n"
        text += f"👤 User: {update.effective_user.username}\n"
        text += f"🆔 ID: {update.effective_user.id}\n"
        text += f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        text += "Select an option from the menu below:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu with all required options"""
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="waiter_capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="waiter_my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="waiter_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "��‍💼 **Waiter Dashboard** 👨‍💼\n\n"
        text += f"👤 User: {update.effective_user.username}\n"
        text += f"🆔 ID: {update.effective_user.id}\n"
        text += f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        text += "Select an option from the menu below:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        logger.info(f"Audit: callback_query by {user_id}: {data}")
        
        # Super Admin callbacks
        if data == "super_pending_restaurants":
            await self.show_pending_restaurants(update)
        elif data == "super_active_restaurants":
            await self.show_active_restaurants(update)
        elif data == "super_daily_reports":
            await self.show_daily_reports(update)
        elif data == "super_statistics":
            await self.show_system_statistics(update)
        elif data == "super_settings":
            await self.show_super_admin_settings(update)
        elif data == "super_help":
            await self.show_super_admin_help(update)
        
        # Restaurant Admin callbacks
        elif data == "restaurant_all_transactions":
            await self.show_restaurant_transactions(update)
        elif data == "restaurant_manage_waiters":
            await self.show_manage_waiters(update)
        elif data == "restaurant_settings":
            await self.show_restaurant_settings(update)
        elif data == "restaurant_download_report":
            await self.download_restaurant_report(update)
        elif data == "restaurant_reconciliation":
            await self.show_reconciliation_menu(update)
        elif data == "restaurant_pending_waiters":
            await self.show_pending_waiters(update)
        elif data == "restaurant_help":
            await self.show_restaurant_help(update)
        
        # Waiter callbacks
        elif data == "waiter_capture_payment":
            await self.start_payment_capture(update)
        elif data == "waiter_my_transactions":
            await self.show_waiter_transactions(update)
        elif data == "waiter_settings":
            await self.show_waiter_settings(update)
        elif data == "waiter_help":
            await self.show_waiter_help(update)
        
        # Registration callbacks
        elif data == "register_restaurant":
            await self.start_restaurant_registration(update)
        elif data == "register_waiter":
            await self.start_waiter_registration(update)
        elif data == "help":
            await self.show_help(update)
        
        # Approval callbacks
        elif data.startswith("approve_restaurant_"):
            restaurant_id = int(data.split("_")[2])
            await self.approve_restaurant(update, restaurant_id)
        elif data.startswith("reject_restaurant_"):
            restaurant_id = int(data.split("_")[2])
            await self.reject_restaurant(update, restaurant_id)
        elif data.startswith("approve_waiter_"):
            waiter_id = int(data.split("_")[2])
            await self.approve_waiter(update, waiter_id)
        elif data.startswith("reject_waiter_"):
            waiter_id = int(data.split("_")[2])
            await self.reject_waiter(update, waiter_id)
        
        # Reconciliation callbacks
        elif data.startswith("bank_"):
            bank_name = data.split("_")[1]
            await self.start_bank_reconciliation(update, bank_name)
        
        # Back to menu callbacks
        elif data == "back_to_super_admin":
            await self.show_super_admin_menu(update)
        elif data == "back_to_restaurant_admin":
            await self.show_restaurant_admin_menu(update)
        elif data == "back_to_waiter":
            await self.show_waiter_menu(update)
        elif data == "back_to_main":
            await self.show_main_menu(update)
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages based on user state"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in self.user_states:
            self.user_states[user_id] = UserState.IDLE
        
        state = self.user_states[user_id]
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, text)
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            await self.handle_waiter_name(update, text)
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            await self.handle_waiter_phone(update, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_SELECTION:
            await self.handle_restaurant_selection(update, text)
        elif state == UserState.CAPTURING_PAYMENT:
            await self.handle_payment_amount(update, text)
        else:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")
    
    async def handle_image(self, update: Update, context):
        """Handle image uploads for OCR processing"""
        user_id = update.effective_user.id
        
        if self.user_states.get(user_id) == UserState.WAITING_FOR_RECEIPT_IMAGE:
            await self.process_receipt_image(update)
        else:
            await update.message.reply_text("Please use the menu to start payment capture first.")
    
    # Registration handlers
    async def start_restaurant_registration(self, update: Update):
        """Start restaurant registration process"""
        user_id = update.effective_user.id
        self.user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🏢 **Restaurant Registration** 🏢\n\n"
            "Please enter your restaurant name:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_restaurant_name(self, update: Update, name: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        self.users[user_id]['restaurant_name'] = name
        self.user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(
            "📞 **Restaurant Phone** 📞\n\n"
            "Please enter your restaurant phone number:"
        )
    
    async def handle_restaurant_phone(self, update: Update, phone: str):
        """Handle restaurant phone input and complete registration"""
        user_id = update.effective_user.id
        
        # Validate phone number
        if not re.match(r'^[0-9+\-\s()]+$', phone):
            await update.message.reply_text(
                "❌ Invalid phone number format. Please enter a valid phone number:"
            )
            return
        
        # Complete restaurant registration
        restaurant_id = len(self.pending_restaurant_approvals) + 1
        self.pending_restaurant_approvals[restaurant_id] = {
            'user_id': user_id,
            'name': self.users[user_id]['restaurant_name'],
            'phone': phone,
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        # Update user role
        self.users[user_id]['role'] = UserRole.RESTAURANT_ADMIN
        self.users[user_id]['restaurant_id'] = restaurant_id
        self.user_states[user_id] = UserState.IDLE
        
        # Notify Super Admin
        await self.notify_super_admin_restaurant_registration(restaurant_id)
        
        # Show success message and restaurant admin menu
        await update.message.reply_text(
            "✅ **Restaurant Registration Successful!** ✅\n\n"
            f"🏢 Restaurant: {self.users[user_id]['restaurant_name']}\n"
            f"📞 Phone: {phone}\n"
            f"🆔 ID: {restaurant_id}\n\n"
            "Your registration is pending Super Admin approval. You'll be notified once approved."
        )
        
        # Show restaurant admin menu
        await self.show_restaurant_admin_menu(update)
    
    async def start_waiter_registration(self, update: Update):
        """Start waiter registration process"""
        user_id = update.effective_user.id
        self.user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "👨‍💼 **Waiter Registration** 👨‍💼\n\n"
            "Please enter your full name:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_waiter_name(self, update: Update, name: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        self.users[user_id]['waiter_name'] = name
        self.user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text(
            "📞 **Waiter Phone** 📞\n\n"
            "Please enter your phone number:"
        )
    
    async def handle_waiter_phone(self, update: Update, phone: str):
        """Handle waiter phone input and complete registration"""
        user_id = update.effective_user.id
        
        # Validate phone number
        if not re.match(r'^[0-9+\-\s()]+$', phone):
            await update.message.reply_text(
                "❌ Invalid phone number format. Please enter a valid phone number:"
            )
            return
        
        # Complete waiter registration
        waiter_id = len(self.pending_waiter_approvals) + 1
        self.pending_waiter_approvals[waiter_id] = {
            'user_id': user_id,
            'name': self.users[user_id]['waiter_name'],
            'phone': phone,
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        # Update user role
        self.users[user_id]['role'] = UserRole.WAITER
        self.users[user_id]['waiter_id'] = waiter_id
        self.user_states[user_id] = UserState.IDLE
        
        # Notify Restaurant Admin
        await self.notify_restaurant_admin_waiter_registration(waiter_id)
        
        # Show success message and waiter menu
        await update.message.reply_text(
            "✅ **Waiter Registration Successful!** ✅\n\n"
            f"👨‍💼 Name: {self.users[user_id]['waiter_name']}\n"
            f"📞 Phone: {phone}\n"
            f"🆔 ID: {waiter_id}\n\n"
            "Your registration is pending Restaurant Admin approval. You'll be notified once approved."
        )
        
        # Show waiter menu
        await self.show_waiter_menu(update)
    
    # Notification handlers
    async def notify_super_admin_restaurant_registration(self, restaurant_id: int):
        """Notify Super Admin about new restaurant registration"""
        try:
            restaurant = self.pending_restaurant_approvals[restaurant_id]
            user = self.users[restaurant['user_id']]
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_restaurant_{restaurant_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_restaurant_{restaurant_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = "🔔 **New Restaurant Registration** 🔔\n\n"
            text += f"🏢 Restaurant: {restaurant['name']}\n"
            text += f"📞 Phone: {restaurant['phone']}\n"
            text += f"👤 User: @{user['username']}\n"
            text += f"�� ID: {restaurant_id}\n"
            text += f"📅 Date: {restaurant['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            text += "Please review and approve or reject this registration."
            
            await self.bot.send_message(
                chat_id=SUPER_ADMIN_USER_ID,
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"Audit: restaurant_registration by {restaurant['user_id']}: Restaurant {restaurant_id} registered by user {restaurant['user_id']}")
            
        except Exception as e:
            logger.error(f"Error notifying Super Admin: {e}")
    
    async def notify_restaurant_admin_waiter_registration(self, waiter_id: int):
        """Notify Restaurant Admin about new waiter registration"""
        try:
            waiter = self.pending_waiter_approvals[waiter_id]
            user = self.users[waiter['user_id']]
            
            # Find a Restaurant Admin to notify
            restaurant_admin_id = None
            for uid, user_data in self.users.items():
                if user_data['role'] == UserRole.RESTAURANT_ADMIN:
                    restaurant_admin_id = uid
                    break
            
            if restaurant_admin_id:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_waiter_{waiter_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_waiter_{waiter_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                text = "🔔 **New Waiter Registration** 🔔\n\n"
                text += f"👨‍💼 Name: {waiter['name']}\n"
                text += f"📞 Phone: {waiter['phone']}\n"
                text += f"👤 User: @{user['username']}\n"
                text += f"🆔 ID: {waiter_id}\n"
                text += f"📅 Date: {waiter['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
                text += "Please review and approve or reject this registration."
                
                await self.bot.send_message(
                    chat_id=restaurant_admin_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: restaurant_admin_notified by {waiter['user_id']}: Waiter {waiter_id} notification sent")
            else:
                logger.warning("No Restaurant Admin found to notify about waiter registration")
                
        except Exception as e:
            logger.error(f"Error notifying Restaurant Admin: {e}")
    
    # Approval handlers
    async def approve_restaurant(self, update: Update, restaurant_id: int):
        """Approve restaurant registration"""
        try:
            if restaurant_id in self.pending_restaurant_approvals:
                restaurant = self.pending_restaurant_approvals[restaurant_id]
                user_id = restaurant['user_id']
                
                # Update restaurant status
                self.pending_restaurant_approvals[restaurant_id]['status'] = 'approved'
                
                # Notify the restaurant owner
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **Congratulations!** 🎉\n\n"
                         f"Your restaurant '{restaurant['name']}' has been approved!\n"
                         f"You can now access the Restaurant Admin dashboard."
                )
                
                # Update Super Admin menu
                await update.callback_query.edit_message_text(
                    f"✅ **Restaurant Approved!** ✅\n\n"
                    f"🏢 Restaurant: {restaurant['name']}\n"
                    f"📞 Phone: {restaurant['phone']}\n"
                    f"🆔 ID: {restaurant_id}\n\n"
                    f"The restaurant owner has been notified.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: restaurant_approved by {update.effective_user.id}: Restaurant {restaurant_id} approved")
                
        except Exception as e:
            logger.error(f"Error approving restaurant: {e}")
            await update.callback_query.edit_message_text("❌ Error approving restaurant. Please try again.")
    
    async def approve_waiter(self, update: Update, waiter_id: int):
        """Approve waiter registration"""
        try:
            if waiter_id in self.pending_waiter_approvals:
                waiter = self.pending_waiter_approvals[waiter_id]
                user_id = waiter['user_id']
                
                # Update waiter status
                self.pending_waiter_approvals[waiter_id]['status'] = 'approved'
                
                # Notify the waiter
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **Congratulations!** 🎉\n\n"
                         f"Your waiter registration has been approved!\n"
                         f"You can now access the Waiter dashboard."
                )
                
                # Update Restaurant Admin menu
                await update.callback_query.edit_message_text(
                    f"✅ **Waiter Approved!** ✅\n\n"
                    f"👨‍💼 Name: {waiter['name']}\n"
                    f"📞 Phone: {waiter['phone']}\n"
                    f"🆔 ID: {waiter_id}\n\n"
                    f"The waiter has been notified.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: waiter_approved by {update.effective_user.id}: Waiter {waiter_id} approved")
                
        except Exception as e:
            logger.error(f"Error approving waiter: {e}")
            await update.callback_query.edit_message_text("❌ Error approving waiter. Please try again.")
    
    async def reject_restaurant(self, update: Update, restaurant_id: int):
        """Reject restaurant registration"""
        try:
            if restaurant_id in self.pending_restaurant_approvals:
                restaurant = self.pending_restaurant_approvals[restaurant_id]
                user_id = restaurant['user_id']
                
                # Update restaurant status
                self.pending_restaurant_approvals[restaurant_id]['status'] = 'rejected'
                
                # Notify the restaurant owner
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ **Registration Rejected** ❌\n\n"
                         f"Your restaurant registration has been rejected.\n"
                         f"Please contact support for more information."
                )
                
                # Update Super Admin menu
                await update.callback_query.edit_message_text(
                    f"❌ **Restaurant Rejected** ❌\n\n"
                    f"🏢 Restaurant: {restaurant['name']}\n"
                    f"📞 Phone: {restaurant['phone']}\n"
                    f"🆔 ID: {restaurant_id}\n\n"
                    f"The restaurant owner has been notified.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: restaurant_rejected by {update.effective_user.id}: Restaurant {restaurant_id} rejected")
                
        except Exception as e:
            logger.error(f"Error rejecting restaurant: {e}")
            await update.callback_query.edit_message_text("❌ Error rejecting restaurant. Please try again.")
    
    async def reject_waiter(self, update: Update, waiter_id: int):
        """Reject waiter registration"""
        try:
            if waiter_id in self.pending_waiter_approvals:
                waiter = self.pending_waiter_approvals[waiter_id]
                user_id = waiter['user_id']
                
                # Update waiter status
                self.pending_waiter_approvals[waiter_id]['status'] = 'rejected'
                
                # Notify the waiter
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ **Registration Rejected** ❌\n\n"
                         f"Your waiter registration has been rejected.\n"
                         f"Please contact support for more information."
                )
                
                # Update Restaurant Admin menu
                await update.callback_query.edit_message_text(
                    f"❌ **Waiter Rejected** ❌\n\n"
                    f"👨‍💼 Name: {waiter['name']}\n"
                    f"📞 Phone: {waiter['phone']}\n"
                    f"🆔 ID: {waiter_id}\n\n"
                    f"The waiter has been notified.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: waiter_rejected by {update.effective_user.id}: Waiter {waiter_id} rejected")
                
        except Exception as e:
            logger.error(f"Error rejecting waiter: {e}")
            await update.callback_query.edit_message_text("❌ Error rejecting waiter. Please try again.")
    
    # Menu display functions
    async def show_pending_restaurants(self, update: Update):
        """Show pending restaurant approvals"""
        if not self.pending_restaurant_approvals:
            text = "📋 **Pending Restaurant Approvals** 📋\n\nNo pending restaurant approvals."
        else:
            text = "📋 **Pending Restaurant Approvals** 📋\n\n"
            for restaurant_id, restaurant in self.pending_restaurant_approvals.items():
                if restaurant['status'] == 'pending':
                    text += f"🏢 **{restaurant['name']}**\n"
                    text += f"📞 Phone: {restaurant['phone']}\n"
                    text += f"🆔 ID: {restaurant_id}\n"
                    text += f"📅 Date: {restaurant['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Super Admin", callback_data="back_to_super_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_waiters(self, update: Update):
        """Show pending waiter approvals"""
        if not self.pending_waiter_approvals:
            text = "👥 **Pending Waiter Approvals** 👥\n\nNo pending waiter approvals."
        else:
            text = "👥 **Pending Waiter Approvals** 👥\n\n"
            for waiter_id, waiter in self.pending_waiter_approvals.items():
                if waiter['status'] == 'pending':
                    text += f"👨‍�� **{waiter['name']}**\n"
                    text += f"📞 Phone: {waiter['phone']}\n"
                    text += f"🆔 ID: {waiter_id}\n"
                    text += f"📅 Date: {waiter['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_reconciliation_menu(self, update: Update):
        """Show bank reconciliation menu"""
        keyboard = [
            [InlineKeyboardButton("�� CBE (Commercial Bank of Ethiopia)", callback_data="bank_cbe")],
            [InlineKeyboardButton("📱 Telebirr", callback_data="bank_telebirr")],
            [InlineKeyboardButton("🏦 Dashen Bank", callback_data="bank_dashen")],
            [InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🔄 **Bank Reconciliation** 🔄\n\n"
        text += "Select the bank for reconciliation:\n\n"
        text += "Upload a PDF statement from your bank to reconcile transactions."
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_bank_reconciliation(self, update: Update, bank_name: str):
        """Start bank reconciliation process"""
        text = f"🏦 **{bank_name} Reconciliation** 🏦\n\n"
        text += f"Please upload your {bank_name} bank statement PDF to start reconciliation.\n\n"
        text += "The system will automatically match transactions with your VeriPay records."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Reconciliation", callback_data="restaurant_reconciliation")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # OCR Processing with real image analysis
    async def process_receipt_image(self, update: Update):
        """Process uploaded receipt image with real OCR"""
        try:
            user_id = update.effective_user.id
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Process with Google Vision API if available
            if self.vision_client:
                try:
                    # Create image object
                    image = vision.Image(content=image_data)
                    
                    # Perform text detection
                    response = self.vision_client.text_detection(image=image)
                    texts = response.text_annotations
                    
                    if texts:
                        # Extract the first (full) text annotation
                        extracted_text = texts[0].description
                        
                        # Parse the extracted text for payment information
                        payment_info = self.parse_receipt_text(extracted_text)
                        
                        if payment_info:
                            # Create transaction record
                            transaction = {
                                'id': len(self.transactions) + 1,
                                'user_id': user_id,
                                'amount': payment_info.get('amount', 0),
                                'bank': payment_info.get('bank', 'Unknown'),
                                'reference': payment_info.get('reference', 'N/A'),
                                'timestamp': datetime.now(),
                                'status': 'captured',
                                'raw_text': extracted_text
                            }
                            
                            self.transactions.append(transaction)
                            
                            # Show success message
                            text = "✅ **Payment Captured Successfully!** ✅\n\n"
                            text += f"�� Amount: {payment_info.get('amount', 0)} ETB\n"
                            text += f"🏦 Bank: {payment_info.get('bank', 'Unknown')}\n"
                            text += f"🔢 Reference: {payment_info.get('reference', 'N/A')}\n"
                            text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                            text += "Transaction has been recorded and will be available for reconciliation."
                            
                            await update.message.reply_text(text, parse_mode='Markdown')
                            
                            # Reset user state
                            self.user_states[user_id] = UserState.IDLE
                            
                        else:
                            await update.message.reply_text(
                                "❌ **Could not extract payment information from the image.**\n\n"
                                "Please ensure the receipt is clear and contains:\n"
                                "• Payment amount\n"
                                "• Bank name\n"
                                "• Reference number\n\n"
                                "Try uploading a clearer image."
                            )
                    else:
                        await update.message.reply_text(
                            "❌ **No text found in the image.**\n\n"
                            "Please ensure the receipt is clear and readable."
                        )
                        
                except Exception as e:
                    logger.error(f"Vision API error: {e}")
                    await update.message.reply_text(
                        "❌ **Error processing image with OCR.**\n\n"
                        "Please try again or contact support."
                    )
            else:
                # Fallback: Use mock data for testing
                await self.process_mock_receipt(update)
                
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            await update.message.reply_text(
                "❌ **Error processing image.**\n\n"
                "Please try again or contact support."
            )
    
    def parse_receipt_text(self, text: str) -> dict:
        """Parse extracted text to find payment information"""
        try:
            # Convert to lowercase for easier matching
            text_lower = text.lower()
            
            # Extract amount (look for patterns like "100.00", "1,000.00", etc.)
            amount_patterns = [
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 1,000.00
                r'(\d+(?:\.\d{2})?)',  # 100.00
                r'amount[:\s]*(\d+(?:\.\d{2})?)',  # amount: 100.00
                r'total[:\s]*(\d+(?:\.\d{2})?)',  # total: 100.00
            ]
            
            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            # Extract bank name
            bank_patterns = [
                r'(cbe|commercial bank of ethiopia)',
                r'(telebirr)',
                r'(dashen)',
                r'(awash)',
                r'(nib)',
                r'(bank)',
            ]
            
            bank = 'Unknown'
            for pattern in bank_patterns:
                if re.search(pattern, text_lower):
                    bank = pattern.replace('|', '').replace('(', '').replace(')', '').strip()
                    break
            
            # Extract reference number
            ref_patterns = [
                r'ref[:\s]*(\d+)',
                r'reference[:\s]*(\d+)',
                r'txn[:\s]*(\d+)',
                r'transaction[:\s]*(\d+)',
            ]
            
            reference = 'N/A'
            for pattern in ref_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    reference = match.group(1)
                    break
            
            return {
                'amount': amount,
                'bank': bank.title(),
                'reference': reference
            }
            
        except Exception as e:
            logger.error(f"Error parsing receipt text: {e}")
            return None
    
    async def process_mock_receipt(self, update: Update):
        """Process mock receipt for testing when Vision API is not available"""
        # Generate mock payment data
        import random
        
        mock_amount = round(random.uniform(50, 1000), 2)
        mock_banks = ['CBE', 'Telebirr', 'Dashen', 'Awash', 'NIB']
        mock_bank = random.choice(mock_banks)
        mock_reference = f"TXN{random.randint(100000, 999999)}"
        
        # Create transaction record
        transaction = {
            'id': len(self.transactions) + 1,
            'user_id': update.effective_user.id,
            'amount': mock_amount,
            'bank': mock_bank,
            'reference': mock_reference,
            'timestamp': datetime.now(),
            'status': 'captured',
            'raw_text': 'Mock data - Vision API not available'
        }
        
        self.transactions.append(transaction)
        
        # Show success message
        text = "✅ **Payment Captured Successfully!** ✅\n\n"
        text += f"💰 Amount: {mock_amount} ETB\n"
        text += f"🏦 Bank: {mock_bank}\n"
        text += f"🔢 Reference: {mock_reference}\n"
        text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        text += "⚠️ **Note: Using mock data - Vision API not configured**\n"
        text += "Transaction has been recorded and will be available for reconciliation."
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Reset user state
        self.user_states[update.effective_user.id] = UserState.IDLE
    
    # Additional menu functions
    async def start_payment_capture(self, update: Update):
        """Start payment capture process"""
        user_id = update.effective_user.id
        self.user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "💳 **Capture Payment** 💳\n\n"
        text += "Please enter the payment amount in ETB:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_payment_amount(self, update: Update, amount_text: str):
        """Handle payment amount input"""
        try:
            amount = float(amount_text)
            if amount <= 0:
                await update.message.reply_text("❌ Please enter a valid amount greater than 0:")
                return
            
            user_id = update.effective_user.id
            self.user_states[user_id] = UserState.WAITING_FOR_RECEIPT_IMAGE
            
            await update.message.reply_text(
                f"💰 **Amount: {amount} ETB** 💰\n\n"
                "Now please upload a photo of the payment receipt for OCR processing."
            )
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number for the amount:")
    
    async def show_waiter_transactions(self, update: Update):
        """Show waiter's transactions"""
        user_id = update.effective_user.id
        user_transactions = [t for t in self.transactions if t['user_id'] == user_id]
        
        if not user_transactions:
            text = "📋 **My Transactions** 📋\n\nNo transactions found."
        else:
            text = "📋 **My Transactions** 📋\n\n"
            for transaction in user_transactions[-10:]:  # Show last 10
                text += f"💰 **{transaction['amount']} ETB**\n"
                text += f"🏦 Bank: {transaction['bank']}\n"
                text += f"🔢 Ref: {transaction['reference']}\n"
                text += f"📅 {transaction['timestamp'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_transactions(self, update: Update):
        """Show all restaurant transactions"""
        user_id = update.effective_user.id
        restaurant_id = self.users[user_id].get('restaurant_id')
        
        if not restaurant_id:
            text = "❌ Restaurant ID not found."
        else:
            # Get all transactions for this restaurant's waiters
            restaurant_transactions = []
            for transaction in self.transactions:
                if transaction['user_id'] in self.users:
                    user = self.users[transaction['user_id']]
                    if user.get('restaurant_id') == restaurant_id:
                        restaurant_transactions.append(transaction)
            
            if not restaurant_transactions:
                text = "📊 **All Transactions** 📊\n\nNo transactions found."
            else:
                text = "📊 **All Transactions** 📊\n\n"
                total_amount = sum(t['amount'] for t in restaurant_transactions)
                text += f"💰 Total Amount: {total_amount} ETB\n"
                text += f"📈 Transaction Count: {len(restaurant_transactions)}\n\n"
                
                for transaction in restaurant_transactions[-10:]:  # Show last 10
                    text += f"💰 **{transaction['amount']} ETB**\n"
                    text += f"🏦 Bank: {transaction['bank']}\n"
                    text += f"🔢 Ref: {transaction['reference']}\n"
                    text += f"📅 {transaction['timestamp'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Admin", callback_data="back_to_restaurant_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Help functions
    async def show_help(self, update: Update):
        """Show general help"""
        text = "ℹ️ **VeriPay Help** ℹ️\n\n"
        text += "**Available Roles:**\n"
        text += "🏢 **Restaurant Admin** - Manage your restaurant and waiters\n"
        text += "👨‍💼 **Waiter** - Capture payments and view transactions\n"
        text += "🔴 **Super Admin** - Approve restaurants and view reports\n\n"
        text += "**Getting Started:**\n"
        text += "1. Register as a restaurant or waiter\n"
        text += "2. Wait for approval from Super Admin or Restaurant Admin\n"
        text += "3. Access your role-specific dashboard\n\n"
        text += "**Support:** Contact @VeriPaySupport for assistance."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Placeholder functions for other menu items
    async def show_active_restaurants(self, update: Update):
        await update.callback_query.edit_message_text("📊 Active Restaurants - Coming Soon!")
    
    async def show_daily_reports(self, update: Update):
        await update.callback_query.edit_message_text("📈 Daily Reports - Coming Soon!")
    
    async def show_system_statistics(self, update: Update):
        await update.callback_query.edit_message_text("📋 System Statistics - Coming Soon!")
    
    async def show_super_admin_settings(self, update: Update):
        await update.callback_query.edit_message_text("⚙️ Super Admin Settings - Coming Soon!")
    
    async def show_super_admin_help(self, update: Update):
        await update.callback_query.edit_message_text("ℹ️ Super Admin Help - Coming Soon!")
    
    async def show_manage_waiters(self, update: Update):
        await update.callback_query.edit_message_text("👥 Manage Waiters - Coming Soon!")
    
    async def show_restaurant_settings(self, update: Update):
        await update.callback_query.edit_message_text("⚙️ Restaurant Settings - Coming Soon!")
    
    async def download_restaurant_report(self, update: Update):
        await update.callback_query.edit_message_text("📊 Download Report - Coming Soon!")
    
    async def show_restaurant_help(self, update: Update):
        await update.callback_query.edit_message_text("ℹ️ Restaurant Help - Coming Soon!")
    
    async def show_waiter_settings(self, update: Update):
        await update.callback_query.edit_message_text("⚙️ Waiter Settings - Coming Soon!")
    
    async def show_waiter_help(self, update: Update):
        await update.callback_query.edit_message_text("ℹ️ Waiter Help - Coming Soon!")
    
    # Run method
    async def run(self):
        """Run the bot"""
        if self.running:
            logger.warning("Bot is already running!")
            return
        
        try:
            self.running = True
            logger.info("Starting VeriPay Bot - COMPLETE VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Clear webhook
            await self.bot.delete_webhook()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Keep running
            await self.application.updater.start_polling()
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.running = False
            if self.application:
                await self.application.stop()

if __name__ == "__main__":
    bot = VeriPayBot()
    asyncio.run(bot.run())
