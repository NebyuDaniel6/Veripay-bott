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
        hint_l = (bank_hint or "").lower()
        text_l = text.lower()
        if "telebirr" in bank_hint_l or "telebirr" in text_l:
            data["bank"] = "Telebirr"
        elif "dashen" in bank_hint_l or "dashen" in text_l:
            data["bank"] = "Dashen Bank"
        elif "abyssinia" in bank_hint_l or "abyssinia" in text_l:
            data["bank"] = "Bank of Abyssinia"
        elif "cbe" in bank_hint_l or "commercial bank" in text_l or "commercial bank of ethiopia" in text_l:
            data["bank"] = "Commercial Bank of Ethiopia"
        else:
            data["bank"] = "Unknown"
        # Amount patterns (ETB before/after, with commas/decimals)
        amount_patterns = [
            r"(?:Amount|Paid|Total)\s*[:\-]?\s*([0-9][\d,]*(?:\.[0-9]{1,2})?)\s*(?:ETB|Birr|Br)?",
            r"(?:ETB|Birr|Br)\s*([0-9][\d,]*(?:\.[0-9]{1,2})?)",
            r"([0-9][\d,]*(?:\.[0-9]{1,2})?)\s*(?:ETB|Birr|Br)"
        ]
        for pat in amount_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["amount"] = m.group(1).replace(',', '')
                break
        # Reference / transaction id patterns
        # Telebirr-specific patterns
        if "telebirr" in text_l:
            # Amount with negative sign and ETB
            telebirr_amount = re.search(r"-([0-9,]+(?:\.[0-9]{2})?)\s*(?:\(ETB\)|ETB)", text)
            if telebirr_amount:
                data["amount"] = telebirr_amount.group(1).replace(",", "")
            
            # Transaction Number format
            telebirr_txn = re.search(r"Transaction\s+Number[:\s]+([A-Z0-9]{8,12})", text, re.IGNORECASE)
            if telebirr_txn:
                data["transaction_id"] = telebirr_txn.group(1)
            
            # Transaction To (recipient)
            telebirr_to = re.search(r"Transaction\s+To[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
            if telebirr_to:
                data["sender"] = telebirr_to.group(1).strip()
            
            # Transaction Time
            telebirr_time = re.search(r"Transaction\s+Time[:\s]+(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", text)
            if telebirr_time:
                data["time"] = telebirr_time.group(1)
        ref_patterns = [
            r"(?:Ref(?:erence)?\s*(?:No\.?|#)?\s*[:\-]?\s*)([A-Za-z0-9\-]{5,})",
            r"(?:Txn(?:\s*ID)?|Transaction(?:\s*ID)?)\s*[:\-]?\s*([A-Za-z0-9\-]{5,})",
            r"(?:Receipt\s*(?:No\.|#)?)\s*[:\-]?\s*([A-Za-z0-9\-]{5,})"
        ]
        for pat in ref_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["transaction_id"] = m.group(1)
                break
        # Sender patterns
        sender_patterns = [
            r"(?:From|Sender|Payer)\s*[:\-]\s*([\w .]+)",
            r"(?:Account\s*Name)\s*[:\-]\s*([\w .]+)"
        ]
        for pat in sender_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["sender"] = m.group(1).strip()
                break
        # Time / date patterns
        time_patterns = [
            r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)\b",
            r"\b(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)\b",
            r"\b(\d{2}-\d{2}-\d{4}\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)\b"
        ]
        for pat in time_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data["time"] = m.group(1)
                break
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
        hint_l = (bank_hint or "").lower()
        # Prefer bank-specific parsers if available
        if (("telebirr" in lower) or ("telebirr" in hint_l)) and telebirr_parser:
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