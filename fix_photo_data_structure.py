#!/usr/bin/env python3
"""
Fix the photo data structure handling
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Fix the photo handling function
old_code = '''        # Get the largest photo size
        photo_sizes = photo.get("photo", [])
        if not photo_sizes:
            send_message(chat_id, "❌ No photo found. Please try again.")
            return
        
        largest_photo = max(photo_sizes, key=lambda x: x.get("width", 0) * x.get("height", 0))'''

new_code = '''        # Get the largest photo size (photo is already an array from Telegram)
        if not photo or not isinstance(photo, list):
            send_message(chat_id, "❌ No photo found. Please try again.")
            return
        
        largest_photo = max(photo, key=lambda x: x.get("width", 0) * x.get("height", 0))'''

# Replace the code
content = content.replace(old_code, new_code)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Photo data structure handling fixed!")
