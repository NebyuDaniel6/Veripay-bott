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
        
        # Method 1: Try individual environment variables (most reliable)
        project_id = os.environ.get('GOOGLE_PROJECT_ID')
        private_key_id = os.environ.get('GOOGLE_PRIVATE_KEY_ID')
        private_key = os.environ.get('GOOGLE_PRIVATE_KEY')
        client_email = os.environ.get('GOOGLE_CLIENT_EMAIL')
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        
        print(f"DEBUG: GOOGLE_PROJECT_ID = {'SET' if project_id else 'NOT SET'}")
        print(f"DEBUG: GOOGLE_PRIVATE_KEY_ID = {'SET' if private_key_id else 'NOT SET'}")
        print(f"DEBUG: GOOGLE_PRIVATE_KEY = {'SET' if private_key else 'NOT SET'}")
        print(f"DEBUG: GOOGLE_CLIENT_EMAIL = {'SET' if client_email else 'NOT SET'}")
        print(f"DEBUG: GOOGLE_CLIENT_ID = {'SET' if client_id else 'NOT SET'}")
        
        if all([project_id, private_key_id, private_key, client_email, client_id]):
            print("✅ All individual environment variables found!")
            try:
                # Clean private key (replace \\n with actual newlines)
                private_key = private_key.replace('\\n', '\n')
                
                # Create credentials info
                creds_info = {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key_id": private_key_id,
                    "private_key": private_key,
                    "client_email": client_email,
                    "client_id": client_id,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
                    "universe_domain": "googleapis.com"
                }
                
                print("🔍 Creating credentials from individual variables...")
                credentials = service_account.Credentials.from_service_account_info(creds_info)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                
                logger.info("✅ Vision OCR initialized from individual environment variables!")
                print("=== VISION OCR INITIALIZATION COMPLETE ===")
                return
                
            except Exception as e:
                print(f"❌ Individual variables failed: {e}")
                print(f"Error type: {type(e).__name__}")
                logger.warning(f"Vision unavailable: Individual variables failed - {e}")
        
        # Method 2: Try JSON environment variable as fallback
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            print(f"✅ Found JSON credentials (length: {len(creds_json)})")
            try:
                # Create temporary file directly from JSON string
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    temp_file.write(creds_json)
                    temp_file_path = temp_file.name
                    
                print(f"✅ Created temporary file: {temp_file_path}")
                
                # Load from file
                credentials = service_account.Credentials.from_service_account_file(temp_file_path)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                
                # Clean up
                os.unlink(temp_file_path)
                
                logger.info("✅ Vision OCR initialized from JSON environment variable!")
                print("=== VISION OCR INITIALIZATION COMPLETE ===")
                return
                
            except Exception as e:
                print(f"❌ JSON method failed: {e}")
                print(f"Error type: {type(e).__name__}")
                logger.warning(f"Vision unavailable: JSON method failed - {e}")
        
        # Method 3: Try file path
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'veripay-credentials.json')
        print(f"🔍 Trying file path: {creds_path}")
        try:
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            self.client = vision.ImageAnnotatorClient(credentials=credentials)
            logger.info("✅ Vision OCR initialized from file!")
            print("=== VISION OCR INITIALIZATION COMPLETE ===")
            return
        except Exception as e:
            print(f"❌ File method failed: {e}")
            logger.warning(f"Vision unavailable: File method failed - {e}")
        
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
