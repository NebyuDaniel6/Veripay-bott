#!/usr/bin/env python3
"""
VeriPay Bot - Fly.io Deployment Wrapper
Simple Flask app that runs the Telegram bot in the background
"""

import os
import threading
import asyncio
from flask import Flask, request, jsonify
from lean_veripay_bot_cloud import LeanVeriPayBot

app = Flask(__name__)

# Global bot instance
bot_instance = None
bot_thread = None

def run_bot():
    """Run the bot in a separate thread"""
    global bot_instance
    try:
        bot_instance = LeanVeriPayBot()
        asyncio.run(bot_instance.start())
    except Exception as e:
        print(f"Bot error: {e}")

@app.route('/')
def home():
    """Home page"""
    return jsonify({
        "status": "running",
        "service": "VeriPay Bot",
        "version": "1.0.0",
        "bot": "@Verifpay_bot"
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot_running": bot_instance is not None
    })

@app.route('/start')
def start_bot():
    """Start the bot"""
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        return jsonify({"status": "Bot started"})
    return jsonify({"status": "Bot already running"})

if __name__ == '__main__':
    # Start the bot in background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False) 