#!/usr/bin/env python3
"""
VeriPay Bot Monitor
Monitors the bot's health and performance
"""

import time
import requests
import yaml
import json
from datetime import datetime
import os

def load_config():
    """Load bot configuration"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def check_bot_status(config):
    """Check if bot is responding to Telegram API"""
    try:
        bot_token = config['telegram']['waiter_bot_token']
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('ok', False)
        return False
    except:
        return False

def check_process():
    """Check if bot process is running"""
    try:
        # Check PID file
        if os.path.exists('veripay_bot.pid'):
            with open('veripay_bot.pid', 'r') as f:
                pid = f.read().strip()
            
            # Check if process exists
            if os.path.exists(f"/proc/{pid}"):
                return True, pid
        return False, None
    except:
        return False, None

def check_logs():
    """Check recent log activity"""
    try:
        log_file = 'logs/bot.log'
        if os.path.exists(log_file):
            # Get file modification time
            mtime = os.path.getmtime(log_file)
            last_modified = datetime.fromtimestamp(mtime)
            
            # Check if log was updated in last 5 minutes
            if (datetime.now() - last_modified).seconds < 300:
                return True, last_modified
        return False, None
    except:
        return False, None

def get_system_info():
    """Get system information"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }
    except ImportError:
        return None

def main():
    """Main monitoring loop"""
    print("🔍 VeriPay Bot Monitor")
    print("=" * 40)
    
    config = load_config()
    if not config:
        print("❌ Cannot load configuration")
        return
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check bot status
        bot_ok = check_bot_status(config)
        process_ok, pid = check_process()
        logs_ok, last_log = check_logs()
        system_info = get_system_info()
        
        # Status indicators
        bot_status = "✅" if bot_ok else "❌"
        process_status = "✅" if process_ok else "❌"
        logs_status = "✅" if logs_ok else "❌"
        
        # Print status
        print(f"\n🕐 {timestamp}")
        print(f"🤖 Bot API: {bot_status}")
        print(f"⚙️  Process: {process_status} {f'(PID: {pid})' if pid else ''}")
        print(f"📝 Logs: {logs_status} {f'(Last: {last_log.strftime('%H:%M:%S')})' if last_log else ''}")
        
        if system_info:
            print(f"💻 CPU: {system_info['cpu_percent']:.1f}% | "
                  f"RAM: {system_info['memory_percent']:.1f}% | "
                  f"Disk: {system_info['disk_percent']:.1f}%")
        
        # Overall status
        if bot_ok and process_ok:
            print("🎉 Bot is healthy!")
        else:
            print("⚠️  Bot needs attention!")
        
        # Wait before next check
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped") 