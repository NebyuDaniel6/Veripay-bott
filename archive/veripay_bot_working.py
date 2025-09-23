#!/usr/bin/env python3
"""
VeriPay Bot - WORKING VERSION
"""

import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc'

class VeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        logger.info(f"User {user_name} ({user_id}) started bot")
        
        keyboard = [
            [InlineKeyboardButton("�� Restaurant Registration", callback_data="register_restaurant")],
            [InlineKeyboardButton("🍳 Waiter Registration", callback_data="register_waiter")],
            [InlineKeyboardButton("🔧 Super Admin Login", callback_data="super_admin_login")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎉 Welcome to VeriPay!\n\nHello {user_name}! 👋\n\nPlease select your role:",
            reply_markup=reply_markup
        )
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "register_restaurant":
            await query.edit_message_text("🏪 Restaurant Registration selected!")
        elif query.data == "register_waiter":
            await query.edit_message_text("🍳 Waiter Registration selected!")
        elif query.data == "super_admin_login":
            await query.edit_message_text("🔧 Super Admin Login selected!")
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        text = update.message.text
        
        logger.info(f"User {user_name} ({user_id}) sent: {text}")
        
        await update.message.reply_text(f"✅ I received your message: {text}")
    
    def run(self):
        """Run the bot"""
        logger.info("Starting VeriPay Bot...")
        logger.info("Send a message to @Verifpay_bot now!")
        
        # Use run_polling for simplicity
        self.application.run_polling()

if __name__ == "__main__":
    # Kill any existing processes
    os.system("pkill -f veripay")
    
    bot = VeriPayBot()
    bot.run()
