import os
import logging
from telegram.ext import Application

# Import your existing functions
from app import create_application

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Debug environment variables
    print("=== ENVIRONMENT VARIABLES DEBUG ===")
    print(f"USE_WEBHOOK: {repr(os.environ.get('USE_WEBHOOK', 'NOT_SET'))}")
    print(f"PUBLIC_URL: {repr(os.environ.get('PUBLIC_URL', 'NOT_SET'))}")
    print(f"PORT: {repr(os.environ.get('PORT', 'NOT_SET'))}")
    print(f"WEBHOOK_PATH: {repr(os.environ.get('WEBHOOK_PATH', 'NOT_SET'))}")
    print(f"BOT_TOKEN: {repr(os.environ.get('BOT_TOKEN', 'NOT_SET')[:10] + '...' if os.environ.get('BOT_TOKEN') else 'NOT_SET')}")
    print("=== END DEBUG ===")
    
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    app = create_application(token)
    print("Bot is running! Press Ctrl+C to stop.")
    use_webhook = os.environ.get("USE_WEBHOOK", "0") == "1"
    print(f"use_webhook evaluated to: {use_webhook}")
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
