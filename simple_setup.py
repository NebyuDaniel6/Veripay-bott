#!/usr/bin/env python3
"""
Simple VeriPay Setup - Minimal setup for testing
"""
import os
import yaml
from pathlib import Path


def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        'uploads',
        'logs',
        'reports',
        'models',
        'backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/")


def test_bot_token():
    """Test the bot token"""
    print("🤖 Testing bot token...")
    
    try:
        import requests
        
        # Load config
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        
        token = config['telegram']['waiter_bot_token']
        
        # Test bot API
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info['ok']:
                print(f"✅ Bot token is valid!")
                print(f"🤖 Bot name: {bot_info['result']['first_name']}")
                print(f"👤 Username: @{bot_info['result']['username']}")
                return True
            else:
                print(f"❌ Bot API error: {bot_info.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing bot token: {e}")
        return False


def create_sample_data():
    """Create sample data for testing"""
    print("📊 Creating sample data...")
    
    try:
        # Create a simple test script
        test_script = """
# Test script for VeriPay
import yaml

# Load config
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

print("✅ Configuration loaded successfully!")
print(f"🤖 Waiter Bot Token: {config['telegram']['waiter_bot_token'][:10]}...")
print(f"👨‍💼 Admin Bot Token: {config['telegram']['admin_bot_token'][:10]}...")

# Test database connection (if available)
try:
    import psycopg2
    print("✅ PostgreSQL driver available")
except ImportError:
    print("⚠️  PostgreSQL driver not installed (optional)")

# Test OCR (if available)
try:
    import cv2
    print("✅ OpenCV available")
except ImportError:
    print("⚠️  OpenCV not installed (optional)")

print("\\n🎉 VeriPay is ready for testing!")
        """
        
        with open('test_veripay.py', 'w') as f:
            f.write(test_script)
        
        print("✅ Test script created: test_veripay.py")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False


def main():
    """Main setup function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    VeriPay Simple Setup                      ║
║                                                              ║
║  Quick setup for testing VeriPay with your bot token        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create directories
    create_directories()
    
    # Test bot token
    if test_bot_token():
        print("\n✅ Bot token is working!")
    else:
        print("\n❌ Bot token test failed. Please check your token.")
        return
    
    # Create sample data
    create_sample_data()
    
    print("""
🎉 VeriPay Simple Setup Complete!

📋 Next Steps:

1. 🤖 Test your bot:
   python3 test_veripay.py

2. 🚀 Start the waiter bot:
   python3 bots/waiter_bot.py

3. 📱 Send /start to your bot on Telegram

4. 📸 Upload a payment screenshot to test

🔗 Your bot should be available at:
https://t.me/YOUR_BOT_USERNAME

Happy testing! 💳✅
    """)


if __name__ == "__main__":
    main() 