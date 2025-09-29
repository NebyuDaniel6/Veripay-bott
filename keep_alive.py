#!/usr/bin/env python3
"""
Keep-alive script to prevent Render free tier from sleeping
Runs every 10 minutes to ping the service
"""
import requests
import time
import os
from datetime import datetime

def ping_service():
    """Ping the service to keep it alive"""
    url = "https://veripay-bott.onrender.com/health"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"[{datetime.now()}] ✅ Service is alive")
            return True
        else:
            print(f"[{datetime.now()}] ⚠️ Service responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Service ping failed: {e}")
        return False

def main():
    """Main keep-alive loop"""
    print(f"[{datetime.now()}] 🚀 Starting keep-alive service...")
    
    while True:
        ping_service()
        # Wait 10 minutes (600 seconds)
        time.sleep(600)

if __name__ == "__main__":
    main()
