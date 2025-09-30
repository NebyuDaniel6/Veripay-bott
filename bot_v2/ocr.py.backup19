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
            print("�� Trying individual environment variables...")
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
