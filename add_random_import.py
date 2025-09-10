#!/usr/bin/env python3
"""
Add missing random import
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Add random import
import_line = "import random\n"
content = content.replace("import uuid", f"import uuid\n{import_line}")

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Random import added!")
