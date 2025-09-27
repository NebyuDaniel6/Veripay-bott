import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from bot_v2.app import create_application

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    app = create_application(token)
    
    if os.environ.get("USE_WEBHOOK", "0") == "1":
        port = int(os.environ.get("PORT", 10000))
        public_url = os.environ.get("PUBLIC_URL")
        webhook_path = os.environ.get("WEBHOOK_PATH", "/webhook")
        
        if public_url:
            print(f"Starting webhook mode on port {port} with URL {public_url}{webhook_path}")
            app.run_webhook(listen="0.0.0.0", port=port, url_path=webhook_path, webhook_url=f"{public_url}{webhook_path}")
        else:
            print("PUBLIC_URL not set, falling back to polling")
            app.run_polling()
    else:
        print("Starting polling mode")
        app.run_polling()
