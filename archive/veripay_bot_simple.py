#!/usr/bin/env python3
"""
VeriPay Bot - SIMPLE WORKING VERSION
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
    IDLE = "idle"

# Global storage
users: Dict[int, Dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, Dict] = {}
pending_waiter_approvals: Dict[int, Dict] = {}
waiter_ids: Dict[int, int] = {}  # waiter_id -> restaurant_id
restaurant_ids: Dict[int, int] = {}  # restaurant_id -> user_id
transactions: List[Dict] = []

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VeriPayBot:
    def __init__(self):
        self.bot = telegram.Bot(token=BOT_TOKEN)
        self.application = None
        self.running = False
        
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"Audit: start_command by {user_id}: User {username} started bot")
        
        # Initialize user
        if user_id not in users:
            users[user_id] = {
                'id': user_id,
                'username': username,
                'role': UserRole.NEW_USER,
                'restaurant_id': None,
                'waiter_id': None,
                'created_at': datetime.now()
            }
        
        # Check if user is Super Admin
        if user_id == SUPER_ADMIN_USER_ID:
            users[user_id]['role'] = UserRole.SUPER_ADMIN
            await self.show_super_admin_menu(update)
        else:
            # Show role selection
            await self.show_role_selection(update)
    
    async def show_role_selection(self, update: Update):
        """Show role selection menu"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍🍳 Register as Waiter", callback_data="register_waiter")],
            [InlineKeyboardButton("ℹ️ About VeriPay", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌟 **Welcome to VeriPay!** 🌟\n\n"
            "Choose your role:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu"""
        keyboard = [
            [InlineKeyboardButton("🏪 Pending Restaurant Approvals", callback_data="super_pending_restaurants")],
            [InlineKeyboardButton("📊 System Statistics", callback_data="super_stats")],
            [InlineKeyboardButton("⚙️ System Settings", callback_data="super_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Super Admin Dashboard** 🔧\n\n"
            "Manage the VeriPay system:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")],
            [InlineKeyboardButton("📊 Restaurant Statistics", callback_data="restaurant_stats")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏪 **Restaurant Admin Dashboard** 🏪\n\n"
            "Manage your restaurant:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_waiter_menu(self, update: Update, context=None):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📊 My Statistics", callback_data="waiter_stats")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="waiter_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👨‍🍳 **Waiter Dashboard** 👨‍🍳\n\n"
            "Manage payments and orders:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "register_restaurant":
            await self.start_restaurant_registration(query)
        elif data == "register_waiter":
            await self.start_waiter_registration(query)
        elif data == "super_pending_restaurants":
            await self.show_pending_restaurants(query)
        elif data == "restaurant_pending_waiters":
            await self.show_pending_waiters(query)
        elif data == "capture_payment":
            await self.start_payment_capture(query)
        else:
            await query.edit_message_text("❌ Unknown action. Please try again.")
    
    async def start_restaurant_registration(self, query):
        """Start restaurant registration process"""
        user_id = query.from_user.id
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        await query.edit_message_text(
            "🏪 **Restaurant Registration** 🏪\n\n"
            "Please enter your restaurant name:",
            parse_mode='Markdown'
        )
    
    async def start_waiter_registration(self, query):
        """Start waiter registration process"""
        user_id = query.from_user.id
        user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        
        await query.edit_message_text(
            "👨‍🍳 **Waiter Registration** 👨‍🍳\n\n"
            "Please enter your full name:",
            parse_mode='Markdown'
        )
    
    async def show_pending_restaurants(self, query):
        """Show pending restaurant approvals"""
        if not pending_restaurant_approvals:
            await query.edit_message_text("✅ No pending restaurant approvals.")
            return
        
        text = "🏪 **Pending Restaurant Approvals** ��\n\n"
        for restaurant_id, data in pending_restaurant_approvals.items():
            text += f"**Restaurant ID:** {restaurant_id}\n"
            text += f"**Name:** {data['name']}\n"
            text += f"**Phone:** {data['phone']}\n"
            text += f"**Owner:** {data['owner_username']}\n\n"
        
        keyboard = []
        for restaurant_id in pending_restaurant_approvals.keys():
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {restaurant_id}", callback_data=f"approve_restaurant_{restaurant_id}"),
                InlineKeyboardButton(f"❌ Reject {restaurant_id}", callback_data=f"reject_restaurant_{restaurant_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_waiters(self, query):
        """Show pending waiter approvals"""
        if not pending_waiter_approvals:
            await query.edit_message_text("✅ No pending waiter approvals.")
            return
        
        text = "👨‍🍳 **Pending Waiter Approvals** 👨‍🍳\n\n"
        for waiter_id, data in pending_waiter_approvals.items():
            text += f"**Waiter ID:** {waiter_id}\n"
            text += f"**Name:** {data['name']}\n"
            text += f"**Phone:** {data['phone']}\n"
            text += f"**Restaurant:** {data['restaurant_name']}\n\n"
        
        keyboard = []
        for waiter_id in pending_waiter_approvals.keys():
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {waiter_id}", callback_data=f"approve_waiter_{waiter_id}"),
                InlineKeyboardButton(f"❌ Reject {waiter_id}", callback_data=f"reject_waiter_{waiter_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_payment_capture(self, query):
        """Start payment capture process"""
        user_id = query.from_user.id
        user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        await query.edit_message_text(
            "💳 **Payment Capture** 💳\n\n"
            "Please send a photo of the payment receipt:",
            parse_mode='Markdown'
        )
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in user_states:
            return
        
        state = user_states[user_id]
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, text)
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            await self.handle_waiter_name(update, text)
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            await self.handle_waiter_phone(update, text)
    
    async def handle_restaurant_name(self, update: Update, name: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_name'] = name
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(
            "📞 **Restaurant Phone** 📞\n\n"
            "Please enter your restaurant phone number:",
            parse_mode='Markdown'
        )
    
    async def handle_restaurant_phone(self, update: Update, phone: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_phone'] = phone
        
        # Generate restaurant ID
        restaurant_id = phone[-4:]  # Last 4 digits of phone
        
        # Store restaurant data
        pending_restaurant_approvals[restaurant_id] = {
            'name': users[user_id]['restaurant_name'],
            'phone': phone,
            'owner_id': user_id,
            'owner_username': users[user_id]['username'],
            'created_at': datetime.now()
        }
        
        logger.info(f"Audit: restaurant_registration by {user_id}: Restaurant {restaurant_id} registered by user {user_id}")
        
        # Notify Super Admin
        await self.notify_super_admin_restaurant_registration(restaurant_id, users[user_id])
        
        # Update user role
        users[user_id]['role'] = UserRole.RESTAURANT_ADMIN
        users[user_id]['restaurant_id'] = restaurant_id
        restaurant_ids[restaurant_id] = user_id
        
        # Show success message and restaurant admin menu
        await update.message.reply_text(
            f"✅ **Restaurant Registered Successfully!** ✅\n\n"
            f"**Restaurant ID:** {restaurant_id}\n"
            f"**Name:** {users[user_id]['restaurant_name']}\n"
            f"**Phone:** {phone}\n\n"
            f"Your restaurant is pending approval from Super Admin.",
            parse_mode='Markdown'
        )
        
        # Show restaurant admin menu
        await self.show_restaurant_admin_menu(update)
        
        # Clear state
        user_states[user_id] = UserState.IDLE
    
    async def handle_waiter_name(self, update: Update, name: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        users[user_id]['waiter_name'] = name
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text(
            "📞 **Waiter Phone** 📞\n\n"
            "Please enter your phone number:",
            parse_mode='Markdown'
        )
    
    async def handle_waiter_phone(self, update: Update, phone: str):
        """Handle waiter phone input"""
        user_id = update.effective_user.id
        users[user_id]['waiter_phone'] = phone
        
        # Generate waiter ID
        waiter_id = phone[-4:]  # Last 4 digits of phone
        
        # Store waiter data
        pending_waiter_approvals[waiter_id] = {
            'name': users[user_id]['waiter_name'],
            'phone': phone,
            'waiter_id': waiter_id,
            'restaurant_name': 'Unknown',  # Will be updated when approved
            'created_at': datetime.now()
        }
        
        logger.info(f"Audit: waiter_registration by {user_id}: Waiter {waiter_id} registered by user {user_id}")
        
        # Notify Restaurant Admin
        await self.notify_restaurant_admin_waiter_registration(waiter_id, users[user_id])
        
        # Update user role
        users[user_id]['role'] = UserRole.WAITER
        users[user_id]['waiter_id'] = waiter_id
        
        # Show success message and waiter menu
        await update.message.reply_text(
            f"✅ **Waiter Registered Successfully!** ✅\n\n"
            f"**Waiter ID:** {waiter_id}\n"
            f"**Name:** {users[user_id]['waiter_name']}\n"
            f"**Phone:** {phone}\n\n"
            f"Your registration is pending approval from Restaurant Admin.",
            parse_mode='Markdown'
        )
        
        # Show waiter menu
        await self.show_waiter_menu(update)
        
        # Clear state
        user_states[user_id] = UserState.IDLE
    
    async def notify_super_admin_restaurant_registration(self, restaurant_id: str, user_data: Dict):
        """Notify Super Admin about new restaurant registration"""
        try:
            message = (
                f"🏪 **New Restaurant Registration** 🏪\n\n"
                f"**Restaurant ID:** {restaurant_id}\n"
                f"**Name:** {user_data['restaurant_name']}\n"
                f"**Phone:** {user_data['restaurant_phone']}\n"
                f"**Owner:** @{user_data['username']}\n\n"
                f"Please review and approve this restaurant."
            )
            
            await self.bot.send_message(
                chat_id=SUPER_ADMIN_USER_ID,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Audit: super_admin_notified by {user_data['id']}: Restaurant {restaurant_id} notification sent")
            
        except Exception as e:
            logger.error(f"Failed to notify Super Admin: {e}")
    
    async def notify_restaurant_admin_waiter_registration(self, waiter_id: str, user_data: Dict):
        """Notify Restaurant Admin about new waiter registration"""
        try:
            # Find restaurant admin (this is simplified - in real app, you'd have proper restaurant-waiter mapping)
            restaurant_admin_id = None
            for rid, uid in restaurant_ids.items():
                if users[uid]['role'] == UserRole.RESTAURANT_ADMIN:
                    restaurant_admin_id = uid
                    break
            
            if restaurant_admin_id:
                message = (
                    f"👨‍🍳 **New Waiter Registration** 👨‍🍳\n\n"
                    f"**Waiter ID:** {waiter_id}\n"
                    f"**Name:** {user_data['waiter_name']}\n"
                    f"**Phone:** {user_data['waiter_phone']}\n"
                    f"**Username:** @{user_data['username']}\n\n"
                    f"Please review and approve this waiter."
                )
                
                await self.bot.send_message(
                    chat_id=restaurant_admin_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Audit: restaurant_admin_notified by {user_data['id']}: Waiter {waiter_id} notification sent")
            else:
                logger.warning("No restaurant admin found to notify about waiter registration")
                
        except Exception as e:
            logger.error(f"Failed to notify Restaurant Admin: {e}")
    
    async def run(self):
        """Run the bot"""
        if self.running:
            logger.warning("Bot is already running!")
            return
        
        try:
            self.running = True
            logger.info("Starting VeriPay Bot - SIMPLE VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Create application
            self.application = Application.builder().token(BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Keep running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.running = False
        finally:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
            self.running = False

if __name__ == "__main__":
    bot = VeriPayBot()
    asyncio.run(bot.run())
