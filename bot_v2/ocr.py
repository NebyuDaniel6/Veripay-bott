import os
import json
import tempfile
from google.cloud import vision
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        print("=== VISION OCR INITIALIZATION ===")
        self.client = None
        
        # Method 1: Try Render secret files with correct paths
        secret_file_paths = [
            '/opt/render/project/src/veripay-credentials.json',
            '/opt/render/project/veripay-credentials.json', 
            './veripay-credentials.json',
            'veripay-credentials.json',
            '/tmp/veripay-credentials.json'
        ]
        
        for creds_path in secret_file_paths:
            print(f"🔍 Trying file path: {creds_path}")
            try:
                if os.path.exists(creds_path):
                    print(f"✅ File exists at: {creds_path}")
                    credentials = service_account.Credentials.from_service_account_file(creds_path)
                    self.client = vision.ImageAnnotatorClient(credentials=credentials)
                    logger.info(f"✅ Vision OCR initialized from file: {creds_path}")
                    print("=== VISION OCR INITIALIZATION COMPLETE ===")
                    return
                else:
                    print(f"❌ File not found at: {creds_path}")
            except Exception as e:
                print(f"❌ Failed to load from {creds_path}: {e}")
        
        # Method 2: Try to create credentials file from environment variable
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            print(f"✅ Found JSON credentials (length: {len(creds_json)})")
            try:
                # Try to write to a known location
                creds_path = '/tmp/veripay-credentials.json'
                with open(creds_path, 'w') as f:
                    f.write(creds_json)
                
                print(f"✅ Created credentials file at: {creds_path}")
                credentials = service_account.Credentials.from_service_account_file(creds_path)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                
                logger.info("✅ Vision OCR initialized from JSON environment variable!")
                print("=== VISION OCR INITIALIZATION COMPLETE ===")
                return
                
            except Exception as e:
                print(f"❌ JSON method failed: {e}")
                print(f"Error type: {type(e).__name__}")
                logger.warning(f"Vision unavailable: JSON method failed - {e}")
        
        # Method 3: Try individual environment variables as last resort
        project_id = os.environ.get('GOOGLE_PROJECT_ID')
        private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
        client_email = os.environ.get('GOOGLE_CLIENT_EMAIL')
        
        if all([project_id, private_key, client_email]):
            print("🔍 Trying individual environment variables...")
            try:
                private_key = private_key.replace('\\n', '\n')
                creds_info = {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key_id": os.environ.get('GOOGLE_PRIVATE_KEY_ID', ''),
                    "private_key": private_key,
                    "client_email": client_email,
                    "client_id": os.environ.get('GOOGLE_CLIENT_ID', ''),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
                    "universe_domain": "googleapis.com"
                }
                
                credentials = service_account.Credentials.from_service_account_info(creds_info)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                
                logger.info("✅ Vision OCR initialized from individual environment variables!")
                print("=== VISION OCR INITIALIZATION COMPLETE ===")
                return
                
            except Exception as e:
                print(f"❌ Individual variables failed: {e}")
                logger.warning(f"Vision unavailable: Individual variables failed - {e}")
        
        logger.warning("Vision unavailable: All methods failed")
        logger.info("Bot will continue without OCR functionality")
        print("=== VISION OCR INITIALIZATION FAILED ===")
        self.client = None

    def extract_text_from_image(self, image_bytes):
        if not self.client:
            return "OCR not available"
        
        try:
            image = vision.Image(content=image_bytes)
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            return texts[0].description if texts else "No text detected"
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return f"OCR error: {e}"

    def extract(self, image_bytes: bytes, bank_hint: str = None) -> dict:
        """Extract structured data from receipt image"""
        if not self.client:
            return {
                "bank": "Unknown",
                "amount": "Unknown", 
                "sender": "Unknown",
                "time": "Unknown",
                "reference": "Unknown",
                "raw_text": "OCR not available"
            }
        
        try:
            # Get raw text from image
            image = vision.Image(content=image_bytes)
            response = self.client.text_detection(image=image)
            texts = response.text_annotations
            full_text = texts[0].description if texts else "No text detected"
            
            print(f"DEBUG: OCR extracted text length: {len(full_text)}")
            print(f"DEBUG: First 200 chars: {repr(full_text[:200])}")
            
            # Parse the text to extract structured data
            parsed_data = self._parse_receipt_text(full_text, bank_hint)
            parsed_data["raw_text"] = full_text
            
            print(f"DEBUG: Parsed data: {parsed_data}")
            return parsed_data
            
        except Exception as e:
            print(f"DEBUG: OCR extraction error: {e}")
            return {
                "bank": "Unknown",
                "amount": "Unknown",
                "sender": "Unknown", 
                "time": "Unknown",
                "reference": "Unknown",
                "raw_text": f"OCR error: {e}"
            }
    
    def _parse_receipt_text(self, text: str, bank_hint: str = None) -> dict:
        """Parse receipt text to extract structured data"""
        import re
        
        # Initialize result
        result = {
            "bank": "Unknown",
            "amount": "Unknown",
            "sender": "Unknown",
            "time": "Unknown", 
            "reference": "Unknown"
        }
        
        text_lower = text.lower()
        
        # Extract bank name
        if "dashen" in text_lower:
            result["bank"] = "Dashen Bank"
        elif "telebirr" in text_lower:
            result["bank"] = "Telebirr"
        elif "cbe" in text_lower or "commercial bank of ethiopia" in text_lower:
            result["bank"] = "Commercial Bank of Ethiopia"
        elif "abyssinia" in text_lower:
            result["bank"] = "Abyssinia Bank"
        elif bank_hint:
            result["bank"] = bank_hint
        
        # Extract amount (look for patterns like "100.00", "1,000.00", etc.)
        amount_patterns = [
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 1,000.00
            r'(\d+(?:\.\d{2})?)',  # 100.00
            r'amount[:\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Amount: 100.00
            r'total[:\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Total: 100.00
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Take the largest amount found
                amounts = [float(match.replace(',', '')) for match in matches]
                if amounts:
                    result["amount"] = f"{max(amounts):.2f}"
                    break
        
        # Extract sender (look for patterns like "From:", "Sender:", etc.)
        sender_patterns = [
            r'from[:\s]*([a-zA-Z\s]+)',
            r'sender[:\s]*([a-zA-Z\s]+)',
            r'paid by[:\s]*([a-zA-Z\s]+)',
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["sender"] = match.group(1).strip()
                break
        
        # Extract time/date
        time_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?)',  # 14:30 or 2:30 PM
            r'(\d{4}-\d{2}-\d{2})',  # 2024-01-15
            r'(\d{1,2}/\d{1,2}/\d{4})',  # 1/15/2024
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                result["time"] = match.group(1)
                break
        
        # Extract reference number with improved Telebirr patterns
        if "telebirr" in text_lower:
            # Telebirr specific patterns - more comprehensive
            telebirr_patterns = [
                r'transaction\s*id[:\s]*(\w+)',
                r'txn\s*id[:\s]*(\w+)',
                r'transaction\s*no[:\s]*(\w+)',
                r'txn\s*no[:\s]*(\w+)',
                r'reference\s*no[:\s]*(\w+)',
                r'ref\s*no[:\s]*(\w+)',
                r'transaction[:\s]*(\d{10,})',
                r'txn[:\s]*(\d{10,})',
                r'(\d{12,})',  # Long numeric IDs
                r'id[:\s]*(\d{10,})',  # Generic ID pattern
                r'no[:\s]*(\d{10,})',  # Generic number pattern
            ]
            for pattern in telebirr_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["reference"] = match.group(1)
                    print(f"DEBUG: Telebirr reference found: {match.group(1)}")
                    break
        else:
            # Generic patterns for other banks
            ref_patterns = [
                r'ref[:\s]*(\w+)',
                r'reference[:\s]*(\w+)',
                r'txn[:\s]*(\w+)',
                r'transaction[:\s]*(\w+)',
            ]
            for pattern in ref_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result["reference"] = match.group(1)
                    break
        
        return result
