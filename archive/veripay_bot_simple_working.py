#!/usr/bin/env python3
"""
Simple VeriPay Bot - Working Version
Just responds to /start command
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"

class SimpleVeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.first_name}) started the bot")
        
        welcome_text = f"🤖 Welcome to VeriPay Bot, {user.first_name}!\n\n"
        welcome_text += "This is a simple working version.\n"
        welcome_text += "The bot is responding correctly!"
        
        await update.message.reply_text(welcome_text)
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting Simple VeriPay Bot...")
        
        # Initialize the application
        await self.application.initialize()
        
        # Start polling
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
        
        try:
            # Keep the bot running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
        finally:
            await self.application.stop()

if __name__ == "__main__":
    bot = SimpleVeriPayBot()
    asyncio.run(bot.run())
