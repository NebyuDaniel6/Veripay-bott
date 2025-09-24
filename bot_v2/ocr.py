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
        
        # Get the JSON from environment variable
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        
        if not creds_json:
            print("❌ No GOOGLE_APPLICATION_CREDENTIALS_JSON found")
            logger.warning("Vision unavailable: No credentials JSON found")
            logger.info("Bot will continue without OCR functionality")
            return
            
        print(f"✅ Found credentials JSON (length: {len(creds_json)})")
        
        try:
            # Create a temporary file with the credentials
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                # Write the JSON directly to the file
                temp_file.write(creds_json)
                temp_file_path = temp_file.name
                
            print(f"✅ Created temporary credentials file: {temp_file_path}")
            
            # Load credentials from the temporary file
            credentials = service_account.Credentials.from_service_account_file(temp_file_path)
            self.client = vision.ImageAnnotatorClient(credentials=credentials)
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            print("✅ Cleaned up temporary file")
            
            logger.info("✅ Vision OCR initialized successfully!")
            print("=== VISION OCR INITIALIZATION COMPLETE ===")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            logger.warning(f"Vision unavailable: Invalid JSON format - {e}")
            logger.info("Bot will continue without OCR functionality")
            self.client = None
            
        except Exception as e:
            print(f"❌ Credentials error: {e}")
            logger.warning(f"Vision unavailable: {e}")
            logger.info("Bot will continue without OCR functionality")
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
