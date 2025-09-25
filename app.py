import os
import logging
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        return jsonify({"status": "ok", "message": "Webhook received"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "veripay-bot"})

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "VeriPay Bot is running", 
        "version": "1.0",
        "endpoints": ["/", "/health", "/webhook"]
    })

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Test endpoint working!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
