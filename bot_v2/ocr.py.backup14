import os
import json
import tempfile
from google.cloud import vision
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        print("DEBUG: Starting VisionOCR initialization")
        self.client = None
        credentials = None

        # Method 1: Debug the JSON environment variable
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            print(f"DEBUG: Raw JSON length: {len(creds_json)}")
            print(f"DEBUG: First 100 chars: {repr(creds_json[:100])}")
            print(f"DEBUG: Last 100 chars: {repr(creds_json[-100:])}")
            
            try:
                # Try to parse as-is first
                creds_dict = json.loads(creds_json)
                print("DEBUG: JSON parsed successfully as-is")
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Vision initialized from JSON environment variable")
                return
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON parse error: {e}")
                print(f"DEBUG: Error position: {e.pos}")
                print(f"DEBUG: Character at error: {repr(creds_json[e.pos:e.pos+10])}")
                
                # Try cleaning the JSON
                try:
                    # Remove all whitespace and line breaks
                    cleaned_json = ''.join(creds_json.split())
                    print(f"DEBUG: Cleaned JSON length: {len(cleaned_json)}")
                    print(f"DEBUG: First 100 chars of cleaned: {repr(cleaned_json[:100])}")
                    
                    creds_dict = json.loads(cleaned_json)
                    print("DEBUG: Cleaned JSON parsed successfully")
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    self.client = vision.ImageAnnotatorClient(credentials=credentials)
                    logger.info("✅ Vision initialized from cleaned JSON environment variable")
                    return
                except Exception as e2:
                    print(f"DEBUG: Cleaned JSON also failed: {e2}")
                    
                    # Try creating temp file approach
                    try:
                        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
                            temp_file.write(cleaned_json)
                            temp_creds_path = temp_file.name
                        print(f"DEBUG: Created temp file: {temp_creds_path}")
                        
                        credentials = service_account.Credentials.from_service_account_file(temp_creds_path)
                        self.client = vision.ImageAnnotatorClient(credentials=credentials)
                        os.unlink(temp_creds_path)
                        logger.info("✅ Vision initialized from temp file")
                        return
                    except Exception as e3:
                        print(f"DEBUG: Temp file approach failed: {e3}")
                        logger.warning(f"❌ All JSON methods failed: {e3}")
            except Exception as e:
                logger.warning(f"❌ Failed to load credentials from JSON: {e}")

        # Fallback to other methods
        logger.warning("Vision unavailable: No valid credentials found")
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
