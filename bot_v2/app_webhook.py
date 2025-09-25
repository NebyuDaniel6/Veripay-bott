import os
import logging
from flask import Flask, request, jsonify
from telegram.ext import ApplicationBuilder, CommandHandler

# Set up logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

async def start(update, context):
    await update.message.reply_text("✅ VeriPay Bot is working!")

async def test(update, context):
    await update.message.reply_text("🧪 Test endpoint working!")

def create_application(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    return app

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"Received webhook data: {data}")
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "veripay-bot"})

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "VeriPay Bot is running", "version": "1.0"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
