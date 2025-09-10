#!/usr/bin/env python3
"""
Test Google Vision API function
"""

import sys
sys.path.append('.')

# Import the function from the bot
from veripay_bot import handle_google_vision_ocr

# Test with a sample image URL
test_image_url = "https://api.telegram.org/file/bot8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc/photos/file_123.jpg"
api_key = "AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M"

print("Testing Google Vision API function...")
try:
    result = handle_google_vision_ocr(test_image_url, api_key)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
