#!/bin/bash
# Keep-alive script for VeriPay bot
# Run this script to keep the Render service alive

echo "🚀 Starting VeriPay Keep-Alive Service"
echo "This will ping the bot every 10 minutes to prevent sleep"
echo "Press Ctrl+C to stop"

while true; do
    echo "[$(date)] Pinging VeriPay bot..."
    curl -s https://veripay-bott.onrender.com/health > /dev/null
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ Bot is alive"
    else
        echo "[$(date)] ❌ Bot ping failed"
    fi
    echo "Waiting 10 minutes..."
    sleep 600
done
