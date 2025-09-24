import os
import json
import tempfile
import base64
from google.cloud import vision
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        print("=== VISION OCR DEBUG START ===")
        self.client = None
        credentials = None

        # Check what environment variables we have
        env_vars = [
            'GOOGLE_APPLICATION_CREDENTIALS_JSON',
            'GOOGLE_APPLICATION_CREDENTIALS_JSON_B64', 
            'GOOGLE_PROJECT_ID',
            'GOOGLE_APPLICATION_CREDENTIALS'
        ]
        
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                print(f"DEBUG: {var} = {repr(value[:50])}... (length: {len(value)})")
            else:
                print(f"DEBUG: {var} = NOT SET")

        # Method 1: Try direct JSON from environment variable
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            print(f"DEBUG: Attempting to parse JSON directly...")
            try:
                # Try parsing as-is
                creds_dict = json.loads(creds_json)
                print("DEBUG: ✅ JSON parsed successfully!")
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Vision initialized from JSON environment variable")
                print("=== VISION OCR DEBUG END (SUCCESS) ===")
                return
            except json.JSONDecodeError as e:
                print(f"DEBUG: ❌ JSON parse error: {e}")
                print(f"DEBUG: Error at position {e.pos}")
                if e.pos < len(creds_json):
                    print(f"DEBUG: Character at error: {repr(creds_json[e.pos:e.pos+20])}")
                
                # Try cleaning the JSON
                try:
                    print("DEBUG: Attempting to clean JSON...")
                    # Remove all whitespace and line breaks
                    cleaned_json = ''.join(creds_json.split())
                    print(f"DEBUG: Cleaned JSON length: {len(cleaned_json)}")
                    
                    creds_dict = json.loads(cleaned_json)
                    print("DEBUG: ✅ Cleaned JSON parsed successfully!")
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    self.client = vision.ImageAnnotatorClient(credentials=credentials)
                    logger.info("✅ Vision initialized from cleaned JSON")
                    print("=== VISION OCR DEBUG END (SUCCESS) ===")
                    return
                except Exception as e2:
                    print(f"DEBUG: ❌ Cleaned JSON failed: {e2}")
            except Exception as e:
                print(f"DEBUG: ❌ Unexpected error: {e}")
                logger.warning(f"❌ Failed to load credentials from JSON: {e}")

        # Method 2: Try Base64 encoded JSON
        creds_b64 = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON_B64')
        if creds_b64:
            print(f"DEBUG: Attempting Base64 decode...")
            try:
                creds_json_decoded = base64.b64decode(creds_b64).decode('utf-8')
                creds_dict = json.loads(creds_json_decoded)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Vision initialized from Base64 JSON")
                print("=== VISION OCR DEBUG END (SUCCESS) ===")
                return
            except Exception as e:
                print(f"DEBUG: ❌ Base64 decode failed: {e}")
                logger.warning(f"❌ Failed to load credentials from Base64: {e}")

        # Method 3: Try individual environment variables
        project_id = os.environ.get('GOOGLE_PROJECT_ID')
        private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
        client_email = os.environ.get('GOOGLE_CLIENT_EMAIL')
        
        if all([project_id, private_key, client_email]):
            print(f"DEBUG: Attempting individual variables...")
            try:
                # Clean private key
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
                logger.info("✅ Vision initialized from individual variables")
                print("=== VISION OCR DEBUG END (SUCCESS) ===")
                return
            except Exception as e:
                print(f"DEBUG: ❌ Individual variables failed: {e}")
                logger.warning(f"❌ Failed to load credentials from individual variables: {e}")

        # Method 4: Try file path
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'veripay-credentials.json')
        print(f"DEBUG: Attempting file path: {creds_path}")
        try:
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            self.client = vision.ImageAnnotatorClient(credentials=credentials)
            logger.info("✅ Vision initialized from file")
            print("=== VISION OCR DEBUG END (SUCCESS) ===")
            return
        except Exception as e:
            print(f"DEBUG: ❌ File path failed: {e}")
            logger.warning(f"❌ Vision unavailable: {e}")

        logger.warning("Vision unavailable: No valid credentials found")
        logger.info("Bot will continue without OCR functionality")
        print("=== VISION OCR DEBUG END (FAILED) ===")
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
