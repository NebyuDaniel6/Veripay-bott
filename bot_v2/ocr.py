import os
import logging
import re
from typing import Optional, Dict, Any
from google.cloud import vision
from google.oauth2 import service_account

# Bank-specific parsers
try:
    from bot_v2.ocr_parsers import dashen as dashen_parser
except Exception:
    dashen_parser = None

try:
    from bot_v2.ocr_parsers import telebirr as telebirr_parser
except Exception:
    telebirr_parser = None

try:
    from bot_v2.ocr_parsers import cbe as cbe_parser
except Exception:
    cbe_parser = None

try:
    from bot_v2.ocr_parsers import abyssinia as abyssinia_parser
except Exception:
    abyssinia_parser = None

logger = logging.getLogger(__name__)

class VisionOCR:
    def __init__(self):
        # Prefer explicit env path
        env_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
        # Common Render secret file location
        render_path = '/opt/render/project/src/veripay-credentials.json'
        # Local cwd fallback
        cwd_path = os.path.join(os.getcwd(), 'veripay-credentials.json')
        # Repo root fallback (this file is in bot_v2/)
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root_path = os.path.join(repo_root, 'veripay-credentials.json')

        candidates = [p for p in [env_path, render_path, cwd_path, root_path] if p]

        credentials = None
        client = None
        last_error = None

        for path in candidates:
            try:
                if os.path.exists(path):
                    credentials = service_account.Credentials.from_service_account_file(path)
                    client = vision.ImageAnnotatorClient(credentials=credentials)
                    logger.info(f"✅ Vision OCR initialized from file: {path}")
                    break
                else:
                    last_error = FileNotFoundError(f"No such file: '{path}'")
            except Exception as e:
                last_error = e
                continue

        if client is None:
            logger.warning(
                "Vision unavailable: %s",
                last_error or "No credential path found"
            )
        self.client = client

    def _fallback_basic(self, text: str, bank_hint: Optional[str]) -> Dict[str, Any]:
        data: Dict[str, Any] = {"raw_text": text}
        bank = (bank_hint or "").lower()
        if "telebirr" in bank:
            data["bank"] = "Telebirr"
        elif "dashen" in bank:
            data["bank"] = "Dashen Bank"
        elif "abyssinia" in bank:
            data["bank"] = "Bank of Abyssinia"
        else:
            data["bank"] = "Unknown"
        # Basic parsers try: amount, reference via regex
        amount_match = re.search(r"(\d+[\.,]?\d*)\s*(?:ETB|Birr|Br)", text, re.IGNORECASE)
        if amount_match:
            data["amount"] = amount_match.group(1).replace(',', '')
        ref_match = re.search(r"(?:Ref(?:erence)?\s*[:#-]?\s*)([A-Za-z0-9-]{5,})", text, re.IGNORECASE)
        if ref_match:
            data["transaction_id"] = ref_match.group(1)
        return data

    def extract_text_from_image(self, image_bytes: bytes) -> Optional[str]:
        if not self.client:
            return None
        image = vision.Image(content=image_bytes)
        response = self.client.document_text_detection(image=image)
        if response.error.message:
            logger.warning("Vision API error: %s", response.error.message)
            return None
        return response.full_text_annotation.text or ""

    def extract(self, image_bytes: bytes, bank_hint: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured data from receipt image."""
        text = self.extract_text_from_image(image_bytes)
        if not text:
            return {"ok": False, "error": "no_text", "message": "OCR failed"}

        lower = text.lower()
        # Prefer bank-specific parsers if available
        if "telebirr" in lower and telebirr_parser:
            try:
                parsed = telebirr_parser.parse(text)
                parsed["raw_text"] = text
                return {"ok": True, **parsed}
            except Exception:
                pass
        if "dashen" in lower and dashen_parser:
            try:
                parsed = dashen_parser.parse(text)
                parsed["raw_text"] = text
                return {"ok": True, **parsed}
            except Exception:
                pass
        if ("commercial bank" in lower or "cbe" in lower) and cbe_parser:
            try:
                parsed = cbe_parser.parse(text)
                parsed["raw_text"] = text
                return {"ok": True, **parsed}
            except Exception:
                pass
        if "abyssinia" in lower and abyssinia_parser:
            try:
                parsed = abyssinia_parser.parse(text)
                parsed["raw_text"] = text
                return {"ok": True, **parsed}
            except Exception:
                pass

        # Fallback generic parsing
        parsed = self._fallback_basic(text, bank_hint)
        parsed["raw_text"] = text
        return {"ok": True, **parsed}
