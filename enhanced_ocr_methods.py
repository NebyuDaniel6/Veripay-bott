# Enhanced OCR Methods for VeriPay Bot
# This file contains improved OCR parsing for CBE, Telebirr, and Dashen Bank receipts

import re
import logging
from datetime import datetime as _dt
from typing import Dict, Optional, Any
from google.cloud import vision

# Try to import pytesseract for fallback
try:
    import pytesseract
    from PIL import Image, ImageOps
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)

async def extract_receipt_data_from_google_vision(self, image_data: bytes) -> Optional[Dict[str, Any]]:
    """Enhanced OCR extraction using Google Vision API with pytesseract fallback"""
    try:
        ocr_text = ""
        
        # Try Google Vision API first
        if self.vision_client:
            try:
                image = vision.Image(content=image_data)
                response = self.vision_client.text_detection(image=image)
                
                if response.error.message:
                    logger.error(f"Vision API error: {response.error.message}")
                else:
                    annotations = response.text_annotations
                    if annotations:
                        ocr_text = annotations[0].description or ""
                        logger.info(f"Google Vision OCR extracted text: {ocr_text[:200]}...")
            except Exception as e:
                logger.error(f"Google Vision API error: {e}")
        
        # Fallback to pytesseract if Google Vision failed or returned empty
        if not ocr_text and OCR_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(image_data))
                # Preprocessing for better OCR
                img = img.convert('L')  # Grayscale
                img = ImageOps.autocontrast(img)  # Auto contrast
                img = img.point(lambda x: 0 if x < 128 else 255, '1')  # Binary threshold
                ocr_text = pytesseract.image_to_string(img, lang='eng')
                logger.info(f"Pytesseract OCR extracted text: {ocr_text[:200]}...")
            except Exception as ocr_err:
                logger.error(f"Pytesseract OCR error: {ocr_err}")
        
        if not ocr_text:
            logger.warning("No OCR text extracted, using fallback data")
            return self.get_fallback_data()
        
        # Parse the extracted text with enhanced parsing
        parsed_data = self.parse_receipt_text_enhanced(ocr_text)
        
        # Convert to the expected format
        result = {
            'amount': float(parsed_data.get('amount', '1000.0')),
            'transaction_id': parsed_data.get('reference', 'UNKNOWN'),
            'date': parsed_data.get('date', _dt.now().strftime('%Y-%m-%d')),
            'time': parsed_data.get('time', _dt.now().strftime('%H:%M')),
            'payer': parsed_data.get('payer', 'Unknown'),
            'receiver': parsed_data.get('receiver', 'Unknown'),
            'bank_name': parsed_data.get('bank', 'Unknown Bank'),
            'payment_method': parsed_data.get('bank', 'Unknown Bank'),
            'currency': 'ETB'
        }
        
        # If datetime_iso is available, parse it to separate date and time
        if 'datetime_iso' in parsed_data:
            try:
                dt = _dt.fromisoformat(parsed_data['datetime_iso'])
                result['date'] = dt.strftime('%Y-%m-%d')
                result['time'] = dt.strftime('%H:%M')
            except Exception as e:
                logger.warning(f"Could not parse datetime_iso: {e}")
        
        logger.info(f"Enhanced OCR extracted data: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in enhanced OCR extraction: {e}")
        return self.get_fallback_data()

def parse_receipt_text_enhanced(self, text: str) -> Dict[str, str]:
    """Enhanced parsing for CBE, Telebirr, and Dashen Bank receipts"""
    result: Dict[str, str] = {}
    if not text:
        return result
    
    try:
        # Normalize text - preserve line breaks for better pattern matching
        lines = text.replace('\r', '\n').split('\n')
        cleaned = ' '.join(line.strip() for line in lines if line.strip())
        
        logger.info(f"Enhanced OCR Text to parse: {cleaned[:300]}...")
        
        # Bank detection patterns
        bank_patterns = [
            (r'dashen|DASHEN', 'Dashen Bank'),
            (r'cbe|CBE|commercial bank|Commercial Bank', 'Commercial Bank of Ethiopia'),
            (r'telebirr|Telebirr|TELEBIRR', 'telebirr'),
            (r'awash|AWASH', 'Awash Bank'),
            (r'abyssinia|ABYSSINIA', 'Abyssinia Bank')
        ]
        
        for pattern, bank_name in bank_patterns:
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                result["bank"] = bank_name
                break
        
        # Enhanced amount patterns - More specific based on actual receipts
        amount_patterns = [
            # CBE: "ETB 10,000.00" - exact pattern
            r'ETB\s+([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',
            # Telebirr: "-7,008.00 (ETB)" or "7,008.00 (ETB)"
            r'(-?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*\(ETB\)',
            # Dashen: "Total: 10,027.60 ETB"
            r'Total:\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*ETB',
            # Generic ETB patterns
            r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*ETB',
            r'ETB\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',
            # Total/Amount labels
            r'(?:Total|Amount|Sum)\s*[:=]?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',
            # Generic number patterns (more restrictive)
            r'\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\b'
        ]
        
        for i, pattern in enumerate(amount_patterns):
            matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
            for match in matches:
                # Clean the number
                num_str = str(match).replace(',', '').replace(' ', '').replace('-', '')
                try:
                    amount = float(num_str)
                    # Skip very small amounts (likely not the main amount)
                    if amount >= 1.0:
                        result["amount"] = str(amount)
                        logger.info(f"Amount found with pattern {i}: {amount}")
                        break
                except ValueError:
                    continue
            if "amount" in result:
                break

        # Enhanced reference / Transaction ID patterns
        ref_patterns = [
            # CBE: "FT25249P26RL" - exact pattern
            r'\bFT[0-9A-Z]{8,15}\b',
            # Dashen: "Transaction Ref: OBTS08022286760791946435"
            r'Transaction Ref:\s*([A-Z0-9]{6,})',
            # Telebirr: "Transaction Number: CHC85K0LMU"
            r'Transaction Number:\s*([A-Z0-9]{6,})',
            # Generic patterns
            r'(?:Ref|Reference|Txn|Transaction|Trans)\s*[:#-]?\s*([A-Z0-9]{6,})',
            r'\b([A-Z0-9]{8,})\b'  # Generic 8+ alphanumeric
        ]
        
        for i, pattern in enumerate(ref_patterns):
            matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
            for match in matches:
                ref = str(match).strip()
                if len(ref) >= 6:  # Minimum length for transaction ID
                    result["reference"] = ref
                    logger.info(f"Reference found with pattern {i}: {ref}")
                    break
            if "reference" in result:
                break

        # Enhanced date/time patterns
        dt_patterns = [
            # CBE: "06/09/2025 at 1..." - partial time
            r'(\d{2}/\d{2}/\d{4})\s+at\s+(\d{1,2})',
            # Telebirr: "2025/08/12 13:23:22" - exact
            r'(\d{4}/\d{2}/\d{2}\s+\d{1,2}:\d{2}:\d{2})',
            # Dashen: "Aug 08, 2025 01:07 PM" - exact
            r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[APap][Mm])',
            # Standard formats
            r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)',
            r'(\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}(?::\d{2})?)',
            r'(\d{2}-\d{2}-\d{4}[ T]\d{2}:\d{2}(?::\d{2})?)'
        ]
        
        dt_found = False
        
        # Try combined date and time first
        for i, pattern in enumerate(dt_patterns):
            matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # CBE partial time format
                    date_part = match[0]
                    time_part = match[1] + ':00'  # Assume :00 for partial time
                    s = f"{date_part} {time_part}"
                else:
                    s = str(match).replace('T', ' ')
                
                # Try various format combinations
                fmts = [
                    "%Y/%m/%d %H:%M:%S",  # Telebirr: 2025/08/12 13:23:22
                    "%d/%m/%Y %H:%M",     # CBE: 06/09/2025 1:00
                    "%b %d, %Y %I:%M %p", # Dashen: Aug 08, 2025 01:07 PM
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"
                ]
                for fmt in fmts:
                    try:
                        dt = _dt.strptime(s, fmt)
                        result["datetime_iso"] = dt.isoformat()
                        result["date"] = dt.strftime('%Y-%m-%d')
                        result["time"] = dt.strftime('%H:%M')
                        dt_found = True
                        logger.info(f"DateTime found with pattern {i}: {result['datetime_iso']}")
                        break
                    except ValueError:
                        continue
                if dt_found:
                    break
            if dt_found:
                break
        
        # Enhanced payer/receiver patterns
        payer_patterns = [
            r'Sender Name:\s*([^\n]+)',
            r'From:\s*([^\n]+)',
            r'debited from\s+([A-Z\s\n]+)',
            r'Transaction To:\s*([^\n]+)'
        ]
        
        for pattern in payer_patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                result["payer"] = match.group(1).strip().replace('\n', ' ')
                break
        
        receiver_patterns = [
            r'Recipient Name:\s*([^\n]+)',
            r'To:\s*([^\n]+)',
            r'for\s+([A-Z\s]+)'
        ]
        
        for pattern in receiver_patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                result["receiver"] = match.group(1).strip()
                break

    except Exception as e:
        logger.error(f"Error in enhanced receipt parsing: {e}")

    return result

def get_fallback_data(self) -> Dict[str, Any]:
    """Enhanced fallback data for testing"""
    return {
        'amount': 1000.0,
        'transaction_id': 'TEST123456',
        'date': _dt.now().strftime('%Y-%m-%d'),
        'time': _dt.now().strftime('%H:%M'),
        'payer': 'Test Payer',
        'receiver': 'Test Receiver',
        'bank_name': 'Test Bank',
        'payment_method': 'Test Bank',
        'currency': 'ETB'
    }
