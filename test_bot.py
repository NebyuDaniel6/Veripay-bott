#!/usr/bin/env python3
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"

async def start_command(update: Update, context):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(f"Received /start from {username} ({user_id})")
    
    await update.message.reply_text(
        f"Hello {username}! Bot is working! 🎉\n\n"
        f"Your ID: {user_id}\n"
        f"Bot is responding to messages correctly!"
    )

async def handle_message(update: Update, context):
    """Handle text messages"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    text = update.message.text
    
    logger.info(f"Received message from {username}: {text}")
    
    await update.message.reply_text(f"Echo: {text}")

def main():
    """Main function"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run bot
    logger.info("Starting test bot...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
