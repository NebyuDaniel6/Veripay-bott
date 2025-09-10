#!/usr/bin/env python3
"""
Fix the Google Vision API key in the bot file
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Replace the API key line
old_line = "GOOGLE_VISION_API_KEY = os.getenv('GOOGLE_VISION_API_KEY', '')"
new_line = "GOOGLE_VISION_API_KEY = 'AIzaSyC4ESpSW_c1ijlLGwTUQ5wdBhflQOPps6M'"

content = content.replace(old_line, new_line)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Google Vision API key fixed in veripay_bot.py!")
