
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

print("\n🎉 VeriPay is ready for testing!")
        