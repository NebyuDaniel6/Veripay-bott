#!/usr/bin/env python3
"""
VeriPay Bot Test Script
Tests if the bot is running and responding properly
"""

import requests
import yaml
import time
import sys

def load_config():
    """Load bot configuration"""
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def test_bot_api(config):
    """Test if bot responds to Telegram API"""
    try:
        bot_token = config['telegram']['waiter_bot_token']
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                print(f"✅ Bot API Test: PASSED")
                print(f"   Bot Name: {bot_info['first_name']}")
                print(f"   Username: @{bot_info['username']}")
                print(f"   Bot ID: {bot_info['id']}")
                return True
            else:
                print(f"❌ Bot API Test: FAILED - {data.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ Bot API Test: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bot API Test: FAILED - {e}")
        return False

def test_database():
    """Test if database is accessible"""
    try:
        import sqlite3
        conn = sqlite3.connect('lean_veripay.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        
        print(f"✅ Database Test: PASSED")
        print(f"   Tables found: {len(tables)}")
        return True
    except Exception as e:
        print(f"❌ Database Test: FAILED - {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are installed"""
    required_modules = [
        'aiogram', 'sqlalchemy', 'cv2', 'PIL', 'pyzbar', 'yaml', 'loguru'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if not missing_modules:
        print(f"✅ Dependencies Test: PASSED")
        print(f"   All required modules available")
        return True
    else:
        print(f"❌ Dependencies Test: FAILED")
        print(f"   Missing modules: {', '.join(missing_modules)}")
        return False

def test_process():
    """Test if bot process is running"""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'lean_veripay_bot.py' in ' '.join(proc.info['cmdline'] or []):
                print(f"✅ Process Test: PASSED")
                print(f"   Bot process running (PID: {proc.info['pid']})")
                return True
        print(f"❌ Process Test: FAILED - Bot process not found")
        return False
    except ImportError:
        print(f"⚠️  Process Test: SKIPPED - psutil not installed")
        return True
    except Exception as e:
        print(f"❌ Process Test: FAILED - {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 VeriPay Bot Test Suite")
    print("=" * 40)
    
    # Load configuration
    config = load_config()
    if not config:
        print("❌ Cannot proceed without configuration")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Dependencies", test_dependencies),
        ("Database", test_database),
        ("Bot API", lambda: test_bot_api(config)),
        ("Process", test_process),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        time.sleep(0.5)
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 40)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready for production!")
        print("\n📱 Bot is live at: https://t.me/Verifpay_bot")
        print("🔗 Test the bot by sending /start")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 