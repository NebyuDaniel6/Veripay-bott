import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

# Set up logging
logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("✅ VeriPay Bot is working!")

async def test(update, context):
    await update.message.reply_text("🧪 Test endpoint working!")

def create_application(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    app = create_application(token)
    print("Bot is running! Press Ctrl+C to stop.")
    
    use_webhook = os.environ.get("USE_WEBHOOK", "0") == "1"
    if use_webhook:
        public_url = os.environ.get("PUBLIC_URL")
        webhook_path = os.environ.get("WEBHOOK_PATH", "/webhook")
        port = int(os.environ.get("PORT", "10000"))
        if not public_url:
            raise ValueError("PUBLIC_URL must be set when USE_WEBHOOK=1")
        print(f"Starting webhook mode on port {port} with URL {public_url}{webhook_path}")
        app.run_webhook(listen="0.0.0.0", port=port, url_path=webhook_path, webhook_url=f"{public_url}{webhook_path}")
    else:
        print("Starting polling mode")
        app.run_polling()
