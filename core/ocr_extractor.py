"""
OCR Extractor for VeriPay - Extracts transaction details from payment screenshots
"""
import cv2
import numpy as np
import pytesseract
import easyocr
from PIL import Image
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import yaml
from loguru import logger


class OCRExtractor:
    """OCR Extractor for payment screenshots"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize OCR extractor"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.ocr_engine = self.config['ai']['ocr_engine']
        self.confidence_threshold = self.config['ai']['confidence_threshold']
        
        # Initialize OCR engines
        if self.ocr_engine == "tesseract":
            pytesseract.pytesseract.tesseract_cmd = self.config['ai']['tesseract_path']
        elif self.ocr_engine == "easyocr":
            self.easyocr_reader = easyocr.Reader(['en', 'am'])  # English and Amharic
        
        # Common patterns for Ethiopian payment systems
        self.patterns = {
            'stn_number': [
                r'STN[:\s]*([A-Z0-9]{8,})',
                r'Transaction[:\s]*([A-Z0-9]{8,})',
                r'Ref[:\s]*([A-Z0-9]{8,})',
                r'([A-Z0-9]{8,})',  # Generic 8+ alphanumeric
            ],
            'amount': [
                r'Amount[:\s]*([0-9,]+\.?[0-9]*)',
                r'Total[:\s]*([0-9,]+\.?[0-9]*)',
                r'([0-9,]+\.?[0-9]*)\s*Birr',
                r'([0-9,]+\.?[0-9]*)\s*ETB',
            ],
            'date': [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
                r'(\d{1,2}\s+\w+\s+\d{4})',
            ],
            'time': [
                r'(\d{1,2}:\d{2}:\d{2})',
                r'(\d{1,2}:\d{2})',
            ],
            'sender': [
                r'From[:\s]*([A-Za-z\s]+)',
                r'Sender[:\s]*([A-Za-z\s]+)',
                r'Account[:\s]*([A-Za-z\s]+)',
            ],
            'receiver': [
                r'To[:\s]*([A-Za-z\s]+)',
                r'Receiver[:\s]*([A-Za-z\s]+)',
                r'Beneficiary[:\s]*([A-Za-z\s]+)',
            ]
        }
    
    def extract_transaction_data(self, image_path: str) -> Dict:
        """
        Extract transaction data from payment screenshot
        
        Returns:
            Dict containing extracted data with confidence scores
        """
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image_path)
            
            # Extract text using OCR
            if self.ocr_engine == "tesseract":
                text_data = self._extract_with_tesseract(processed_image)
            elif self.ocr_engine == "easyocr":
                text_data = self._extract_with_easyocr(processed_image)
            else:
                raise ValueError(f"Unsupported OCR engine: {self.ocr_engine}")
            
            # Parse extracted text
            extracted_data = self._parse_text_data(text_data)
            
            # Determine bank type
            bank_type = self._detect_bank_type(text_data['full_text'])
            
            # Calculate overall confidence
            overall_confidence = self._calculate_confidence(extracted_data)
            
            return {
                'stn_number': extracted_data.get('stn_number'),
                'amount': extracted_data.get('amount'),
                'transaction_date': extracted_data.get('transaction_date'),
                'sender_account': extracted_data.get('sender_account'),
                'receiver_account': extracted_data.get('receiver_account'),
                'bank_type': bank_type,
                'full_text': text_data['full_text'],
                'confidence': overall_confidence,
                'extraction_details': extracted_data
            }
            
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            return {
                'error': str(e),
                'confidence': 0.0
            }
    
    def _preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply noise reduction
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return cleaned
    
    def _extract_with_tesseract(self, image: np.ndarray) -> Dict:
        """Extract text using Tesseract OCR"""
        # Configure Tesseract for better accuracy
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\s\.\,\:\-\/'
        
        # Extract text
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # Get confidence scores
        data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'full_text': text,
            'confidence': avg_confidence / 100.0,  # Normalize to 0-1
            'words': data['text'],
            'word_confidences': data['conf']
        }
    
    def _extract_with_easyocr(self, image: np.ndarray) -> Dict:
        """Extract text using EasyOCR"""
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(image)
        
        # Extract text
        results = self.easyocr_reader.readtext(np.array(pil_image))
        
        # Combine all text
        full_text = ' '.join([result[1] for result in results])
        
        # Calculate average confidence
        confidences = [result[2] for result in results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'full_text': full_text,
            'confidence': avg_confidence,
            'results': results
        }
    
    def _parse_text_data(self, text_data: Dict) -> Dict:
        """Parse extracted text to find transaction details"""
        full_text = text_data['full_text']
        extracted_data = {}
        
        # Extract STN Number
        stn_number = self._extract_pattern(full_text, self.patterns['stn_number'])
        if stn_number:
            extracted_data['stn_number'] = stn_number
        
        # Extract Amount
        amount_str = self._extract_pattern(full_text, self.patterns['amount'])
        if amount_str:
            try:
                # Clean amount string and convert to float
                amount_clean = amount_str.replace(',', '').replace(' ', '')
                extracted_data['amount'] = float(amount_clean)
            except ValueError:
                logger.warning(f"Could not parse amount: {amount_str}")
        
        # Extract Date and Time
        date_str = self._extract_pattern(full_text, self.patterns['date'])
        time_str = self._extract_pattern(full_text, self.patterns['time'])
        
        if date_str:
            try:
                # Parse date
                transaction_date = self._parse_date(date_str, time_str)
                if transaction_date:
                    extracted_data['transaction_date'] = transaction_date
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
        
        # Extract Sender Account
        sender = self._extract_pattern(full_text, self.patterns['sender'])
        if sender:
            extracted_data['sender_account'] = sender.strip()
        
        # Extract Receiver Account
        receiver = self._extract_pattern(full_text, self.patterns['receiver'])
        if receiver:
            extracted_data['receiver_account'] = receiver.strip()
        
        return extracted_data
    
    def _extract_pattern(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract text using regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        return None
    
    def _parse_date(self, date_str: str, time_str: str = None) -> Optional[datetime]:
        """Parse date and time strings"""
        try:
            # Common date formats
            date_formats = [
                '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d', '%y/%m/%d',
                '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d', '%y-%m-%d',
                '%d %B %Y', '%d %b %Y'
            ]
            
            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    
                    # Add time if provided
                    if time_str:
                        try:
                            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
                            date_obj = date_obj.replace(hour=time_obj.hour, 
                                                       minute=time_obj.minute, 
                                                       second=time_obj.second)
                        except ValueError:
                            try:
                                time_obj = datetime.strptime(time_str, '%H:%M').time()
                                date_obj = date_obj.replace(hour=time_obj.hour, 
                                                           minute=time_obj.minute)
                            except ValueError:
                                pass
                    
                    return date_obj
                except ValueError:
                    continue
            
            return None
        except Exception as e:
            logger.warning(f"Error parsing date: {e}")
            return None
    
    def _detect_bank_type(self, text: str) -> str:
        """Detect bank type from text"""
        text_lower = text.lower()
        
        if 'cbe' in text_lower or 'commercial bank' in text_lower:
            return 'cbe'
        elif 'telebirr' in text_lower or 'ethio telecom' in text_lower:
            return 'telebirr'
        elif 'dashen' in text_lower or 'dashen bank' in text_lower:
            return 'dashen'
        else:
            return 'other'
    
    def _calculate_confidence(self, extracted_data: Dict) -> float:
        """Calculate overall confidence score"""
        confidence_scores = []
        
        # Base confidence for each extracted field
        if extracted_data.get('stn_number'):
            confidence_scores.append(0.8)
        if extracted_data.get('amount'):
            confidence_scores.append(0.9)
        if extracted_data.get('transaction_date'):
            confidence_scores.append(0.7)
        if extracted_data.get('sender_account'):
            confidence_scores.append(0.6)
        if extracted_data.get('receiver_account'):
            confidence_scores.append(0.6)
        
        # Return average confidence
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    def validate_extraction(self, extracted_data: Dict) -> Tuple[bool, List[str]]:
        """Validate extracted data and return issues"""
        issues = []
        
        # Check required fields
        if not extracted_data.get('stn_number'):
            issues.append("STN number not found")
        
        if not extracted_data.get('amount'):
            issues.append("Amount not found")
        elif extracted_data['amount'] <= 0:
            issues.append("Invalid amount (must be positive)")
        
        if not extracted_data.get('transaction_date'):
            issues.append("Transaction date not found")
        
        # Check for reasonable values
        if extracted_data.get('amount') and extracted_data['amount'] > 1000000:
            issues.append("Amount seems unusually high")
        
        # Check date is not in future
        if extracted_data.get('transaction_date'):
            if extracted_data['transaction_date'] > datetime.now():
                issues.append("Transaction date is in the future")
        
        is_valid = len(issues) == 0
        return is_valid, issues 