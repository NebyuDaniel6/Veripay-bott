import os
import logging
import re
from typing import Optional, Dict, Any
from google.cloud import vision
from google.oauth2 import service_account

# Bank-specific parsers
# Prefer local imports; fall back to absolute to support both local and packaged runs
try:
    from ocr_parsers import dashen as dashen_parser  # local
except Exception:
    try:
        from bot_v2.ocr_parsers import dashen as dashen_parser  # absolute
    except Exception:
        dashen_parser = None

try:
    from ocr_parsers import telebirr as telebirr_parser
except Exception:
    try:
        from bot_v2.ocr_parsers import telebirr as telebirr_parser
    except Exception:
        telebirr_parser = None

try:
    from ocr_parsers import cbe as cbe_parser
except Exception:
    try:
        from bot_v2.ocr_parsers import cbe as cbe_parser
    except Exception:
        cbe_parser = None

try:
    from ocr_parsers import abyssinia as abyssinia_parser
except Exception:
    try:
        from bot_v2.ocr_parsers import abyssinia as abyssinia_parser
    except Exception:
        abyssinia_parser = None

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(creds_dict)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("Vision initialized from environment variable JSON")
                return
            except Exception as e:
                logger.warning(f"Failed to load credentials from JSON: {e}")
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '/Users/macbook/veripay/veripay-credentials.json')
        try:
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            self.client = vision.ImageAnnotatorClient(credentials=credentials)
        except Exception as e:
            logger.warning(f"Vision unavailable: {e}")
            self.client = None

    def _fallback_basic(self, text: str, bank_hint: Optional[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"raw_text": text}
        bank = (bank_hint or "").lower()
        if "telebirr" in bank or "telebirr" in text.lower():
            data["bank"] = "Telebirr"
        elif "dashen" in bank or "dashen" in text.lower():
            data["bank"] = "Dashen Bank"
        elif "abyssinia" in bank or "bank of abyssinia" in text.lower():
            data["bank"] = "Bank of Abyssinia"
        else:
            data["bank"] = "Commercial Bank of Ethiopia" if ("cbe" in bank or "commercial bank of ethiopia" in text.lower()) else "Unknown"
        return data

    def extract(self, image_bytes: bytes, bank_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        image = vision.Image(content=image_bytes)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations or []
        if not texts:
            return None
        full_text = texts[0].description
        bank_l = (bank_hint or "").lower()

        # Dispatch to bank-specific parser
        try:
            if "dashen" in bank_l and dashen_parser:
                parsed = dashen_parser.extract_fields(full_text)
            elif "telebirr" in bank_l and telebirr_parser:
                parsed = telebirr_parser.extract_fields(full_text)
            elif ("cbe" in bank_l or "commercial bank of ethiopia" in bank_l) and cbe_parser:
                parsed = cbe_parser.extract_fields(full_text)
            elif "abyssinia" in bank_l and abyssinia_parser:
                parsed = abyssinia_parser.extract_fields(full_text)
            else:
                # Try lightweight auto-detect when hint is missing
                auto = self._fallback_basic(full_text, bank_hint)
                b = auto.get("bank", "").lower()
                if "dashen" in b and dashen_parser:
                    parsed = dashen_parser.extract_fields(full_text)
                elif "telebirr" in b and telebirr_parser:
                    parsed = telebirr_parser.extract_fields(full_text)
                elif "abyssinia" in b and abyssinia_parser:
                    parsed = abyssinia_parser.extract_fields(full_text)
                elif "commercial bank of ethiopia" in b and cbe_parser:
                    parsed = cbe_parser.extract_fields(full_text)
                else:
                    parsed = auto
        except Exception as e:
            logger.warning(f"Parser error for bank '{bank_hint}': {e}")
            parsed = self._fallback_basic(full_text, bank_hint)

        parsed["raw_text"] = full_text
        return parsed
