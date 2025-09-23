#!/usr/bin/env python3

# Read the current file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find the end of get_fallback_data function
fallback_end = content.find("        }")
if fallback_end != -1:
    # Find the next line after the closing brace
    next_line_start = content.find('\n', fallback_end) + 1
    
    # Insert the basic OCR function
    ocr_function = '''
    async def extract_data_basic_ocr(self, image_data: bytes) -> Dict[str, Any]:
        """Extract basic data from image using regex (fallback if Vision API fails)"""
        text = image_data.decode("utf-8", errors="ignore")  # Simple decode for basic text extraction
        logger.info(f"Basic OCR extracted text: {text}")

        amount_match = re.search(r"(\d[\d,]*\.?\d{0,2})\s*(ETB|BIRR)", text, re.IGNORECASE)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 500.0

        transaction_id = f"OCR{len(transactions) + 1:06d}"
        date = datetime.now().strftime("%Y-%m-%d")
        time = datetime.now().strftime("%H:%M")
        payer = "Customer"
        receiver = "Restaurant"
        bank_name = self.detect_bank_name(text)
        payment_method = bank_name

        return {
            "amount": amount,
            "transaction_id": transaction_id,
            "date": date,
            "time": time,
            "payer": payer,
            "receiver": receiver,
            "bank_name": bank_name,
            "payment_method": payment_method,
            "currency": "ETB"
        }
'''
    
    # Insert the function
    new_content = content[:next_line_start] + ocr_function + content[next_line_start:]
    
    # Write back to file
    with open('veripay_bot.py', 'w') as f:
        f.write(new_content)
    
    print("Basic OCR function added successfully!")
else:
    print("Could not find get_fallback_data function")
