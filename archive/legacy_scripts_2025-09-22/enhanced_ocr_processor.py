#!/usr/bin/env python3
"""
Enhanced OCR Processor for VeriPay Bot
- Improved text parsing patterns for Ethiopian banks
- Better fallback methods
- Enhanced error handling
"""

import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedOCRProcessor:
    """Enhanced OCR processor with improved parsing patterns"""
    
    def __init__(self):
        # Enhanced bank patterns for Ethiopian banks
        self.bank_patterns = [
            (r'(commercial bank of ethiopia|cbe)', 'Commercial Bank of Ethiopia'),
            (r'(telebirr)', 'Telebirr'),
            (r'(dashen bank|dashen)', 'Dashen Bank'),
            (r'(awash bank|awash)', 'Awash Bank'),
            (r'(nib|national bank)', 'National Bank'),
            (r'(united bank|ub)', 'United Bank'),
            (r'(bank of abyssinia|boa)', 'Bank of Abyssinia'),
            (r'(wegagen bank)', 'Wegagen Bank'),
            (r'(cooperative bank of oromia|cbo)', 'Cooperative Bank of Oromia'),
            (r'(zemen bank)', 'Zemen Bank'),
            (r'(bunna international bank)', 'Bunna International Bank'),
            (r'(berhan international bank)', 'Berhan International Bank'),
            (r'(lion international bank)', 'Lion International Bank'),
            (r'(shabelle bank)', 'Shabelle Bank'),
            (r'(amhara bank)', 'Amhara Bank'),
        ]
        
        # Enhanced amount patterns
        self.amount_patterns = [
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:etb|birr|br)',
            r'(?:amount|total|paid|debit|credit)[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:etb|birr|br)',
            r'(\d+(?:\.\d{2})?)\s*(?:etb|birr|br)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        # Enhanced reference patterns
        self.reference_patterns = [
            r'ref[:\s]*(\d+)',
            r'reference[:\s]*(\d+)',
            r'txn[:\s]*(\d+)',
            r'transaction[:\s]*(\d+)',
            r'id[:\s]*(\d+)',
            r'(\d{10,})',  # Long numeric IDs
            r'ft(\d+)',  # CBE transaction IDs
            r't(\d+)',  # Transaction IDs
        ]
    
    def extract_payment_info(self, text: str) -> Dict:
        """Extract payment information from text"""
        try:
            text_lower = text.lower()
            
            # Extract amount
            amount = self._extract_amount(text_lower)
            
            # Extract bank
            bank = self._extract_bank(text_lower)
            
            # Extract reference
            reference = self._extract_reference(text_lower)
            
            return {
                'amount': amount,
                'bank': bank,
                'reference': reference,
                'raw_text': text
            }
            
        except Exception as e:
            logger.error(f"Error extracting payment info: {e}")
            return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text"""
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the amount string
                    amount_str = match.replace(',', '').strip()
                    amount = float(amount_str)
                    if amount > 0:  # Valid amount
                        return amount
                except ValueError:
                    continue
        return None
    
    def _extract_bank(self, text: str) -> str:
        """Extract bank name from text"""
        for pattern, bank_name in self.bank_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return bank_name
        return 'Unknown Bank'
    
    def _extract_reference(self, text: str) -> str:
        """Extract reference number from text"""
        for pattern in self.reference_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return 'N/A'
    
    def process_cbe_receipt(self, text: str) -> Dict:
        """Special processing for CBE receipts"""
        try:
            # CBE specific patterns
            cbe_patterns = {
                'amount': [
                    r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:etb|birr)',
                    r'amount[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                    r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*etb',
                ],
                'reference': [
                    r'ft(\d+)',
                    r'transaction[:\s]*id[:\s]*(\d+)',
                    r'ref[:\s]*(\d+)',
                ]
            }
            
            amount = None
            for pattern in cbe_patterns['amount']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            reference = 'N/A'
            for pattern in cbe_patterns['reference']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    reference = match.group(1)
                    break
            
            return {
                'amount': amount,
                'bank': 'Commercial Bank of Ethiopia',
                'reference': reference,
                'raw_text': text
            }
            
        except Exception as e:
            logger.error(f"Error processing CBE receipt: {e}")
            return None

# Test the processor
if __name__ == "__main__":
    processor = EnhancedOCRProcessor()
    
    # Test with sample CBE receipt text
    sample_text = """
    Commercial Bank of Ethiopia
    Transaction Receipt
    Amount: 10,000.00 ETB
    Reference: FT25249P26RL
    Date: 06-Sep-2025
    """
    
    result = processor.extract_payment_info(sample_text)
    print("Enhanced OCR Result:", result)
    
    # Test CBE specific processing
    cbe_result = processor.process_cbe_receipt(sample_text)
    print("CBE Specific Result:", cbe_result)
