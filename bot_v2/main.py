import asyncio
import logging
import os
from bot_v2.app import create_application

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    token = os.environ.get('BOT_TOKEN')
    if not token:
        raise RuntimeError('BOT_TOKEN not set')
    app = create_application(token)

    use_webhook = os.environ.get('USE_WEBHOOK', '0') == '1'
    public_url = os.environ.get('PUBLIC_URL', '')
    # Handle empty or invalid PORT
    port_env = os.environ.get('PORT', '').strip()
    try:
        port = int(port_env) if port_env else 8080
    except ValueError:
        port = 8080
    path = os.environ.get('WEBHOOK_PATH', '/')

    if use_webhook and public_url:
        print(f"Starting webhook at {public_url}{path} on port {port}")
        app.run_webhook(
            listen='0.0.0.0',
            port=port,
            url_path=path.lstrip('/'),
            webhook_url=f"{public_url.rstrip('/')}/{path.lstrip('/')}",
            drop_pending_updates=True
        )
    else:
        print("Starting polling mode")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
