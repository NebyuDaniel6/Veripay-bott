#!/usr/bin/env python3
"""
Fix the Google Vision function to return the correct format
"""

import re

# Read the current bot file
with open('veripay_bot.py', 'r') as f:
    content = f.read()

# Find and replace the Google Vision function
old_function = '''def handle_google_vision_ocr(image_url: str, api_key: str) -> Dict[str, Any]:
    """Process image with Google Vision API"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        image_data = response.content
        
        # Convert to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Call Google Vision API
        vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        payload = {
            "requests": [{
                "image": {"content": base64_image},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                ]
            }]
        }
        
        response = requests.post(vision_url, json=payload, timeout=10)
        result = response.json()
        
        if "responses" in result and result["responses"]:
            response_data = result["responses"][0]
            text_annotations = response_data.get("textAnnotations", [])
            full_text = text_annotations[0].get("description", "") if text_annotations else ""
            
            return {
                "full_text": full_text,
                "confidence": 0.8,
                "processed_at": datetime.now().isoformat()
            }
        
        return {
            "full_text": "No text detected",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing image with Google Vision: {e}")
        return {
            "full_text": "Error processing image",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }'''

new_function = '''def handle_google_vision_ocr(image_url: str, api_key: str) -> Dict[str, Any]:
    """Process image with Google Vision API and extract receipt data"""
    try:
        # Download image
        response = requests.get(image_url, timeout=10)
        image_data = response.content
        
        # Convert to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Call Google Vision API
        vision_url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
        payload = {
            "requests": [{
                "image": {"content": base64_image},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 10}
                ]
            }]
        }
        
        response = requests.post(vision_url, json=payload, timeout=10)
        result = response.json()
        
        if "responses" in result and result["responses"]:
            response_data = result["responses"][0]
            text_annotations = response_data.get("textAnnotations", [])
            full_text = text_annotations[0].get("description", "") if text_annotations else ""
            
            # Extract receipt data from the text
            receipt_data = extract_receipt_data_from_google_vision(full_text)
            
            return {
                "amount": receipt_data.get('amount', 0.0),
                "currency": receipt_data.get('currency', 'ETB'),
                "transaction_id": receipt_data.get('transaction_id', ''),
                "payer": receipt_data.get('payer', ''),
                "receiver": receipt_data.get('receiver', ''),
                "full_text": full_text,
                "confidence": 0.8,
                "processed_at": datetime.now().isoformat()
            }
        
        return {
            "amount": 0.0,
            "currency": "ETB",
            "transaction_id": "",
            "payer": "",
            "receiver": "",
            "full_text": "No text detected",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing image with Google Vision: {e}")
        return {
            "amount": 0.0,
            "currency": "ETB",
            "transaction_id": "",
            "payer": "",
            "receiver": "",
            "full_text": "Error processing image",
            "confidence": 0.0,
            "processed_at": datetime.now().isoformat()
        }'''

# Replace the function
content = content.replace(old_function, new_function)

# Write the updated content back to the file
with open('veripay_bot.py', 'w') as f:
    f.write(content)

print("Google Vision function fixed to return correct format!")
