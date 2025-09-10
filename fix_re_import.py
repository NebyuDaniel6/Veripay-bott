#!/usr/bin/env python3
"""
Add missing re import
"""

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Add re import
import_line = "import re\n"
content = content.replace("import random", f"import random\n{import_line}")

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("re import added!")
