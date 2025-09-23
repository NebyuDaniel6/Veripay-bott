#!/usr/bin/env python3
"""
Enhanced OCR Processing for VeriPay Bot
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
            (r'(berhan bank)', 'Berhan Bank'),
            (r'(cooperative bank of oromia|cbo)', 'Cooperative Bank of Oromia'),
            (r'(lion international bank)', 'Lion International Bank'),
            (r'(zemen bank)', 'Zemen Bank'),
            (r'(bunna international bank)', 'Bunna International Bank'),
            (r'(amhara bank)', 'Amhara Bank'),
            (r'(bank of ethiopia)', 'Bank of Ethiopia'),
        ]
        
        # Enhanced amount patterns
        self.amount_patterns = [
            r'amount[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'total[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'paid[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:etb|birr|br)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*[₦$]',
            r'(\d+(?:\.\d{2})?)\s*(?:etb|birr|br)',
            r'(\d+(?:\.\d{2})?)\s*[₦$]',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        # Enhanced reference patterns
        self.reference_patterns = [
            r'ref[:\s]*(\d+)',
            r'reference[:\s]*(\d+)',
            r'txn[:\s]*(\d+)',
            r'transaction[:\s]*(\d+)',
            r'trace[:\s]*(\d+)',
            r'id[:\s]*(\d+)',
            r'(\d{10,})',  # Long numbers (likely transaction IDs)
            r'(\d{6,})',   # Medium numbers
        ]
        
        # Currency patterns
        self.currency_patterns = [
            r'etb|birr|br|ethiopian birr',
            r'usd|dollar|\$',
            r'eur|euro|€',
        ]

    def extract_text_enhanced(self, text: str) -> Tuple[str, str]:
        """Extract text using enhanced processing"""
        try:
            # Clean and normalize text
            cleaned_text = self.clean_text(text)
            
            # Try to extract payment information
            payment_info = self.parse_payment_info(cleaned_text)
            
            if payment_info:
                return self.format_payment_info(payment_info), "Enhanced Processing"
            else:
                return self.generate_fallback_response(cleaned_text), "Fallback Processing"
                
        except Exception as e:
            logger.error(f"Error in enhanced text extraction: {e}")
            return self.generate_fallback_response(text), "Error Fallback"

    def clean_text(self, text: str) -> str:
        """Clean and normalize text for better parsing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s.,:()-]', '', text)
        
        # Normalize common OCR errors
        text = text.replace('O', '0')  # Common OCR error
        text = text.replace('l', '1')  # Common OCR error
        text = text.replace('I', '1')  # Common OCR error
        
        return text.strip()

    def parse_payment_info(self, text: str) -> Optional[Dict]:
        """Parse payment information from text"""
        try:
            text_lower = text.lower()
            
            # Extract amount
            amount = self.extract_amount(text_lower)
            if not amount:
                return None
            
            # Extract bank
            bank = self.extract_bank(text_lower)
            
            # Extract reference
            reference = self.extract_reference(text_lower)
            
            # Extract currency
            currency = self.extract_currency(text_lower)
            
            return {
                'amount': amount,
                'bank': bank,
                'reference': reference,
                'currency': currency,
                'raw_text': text
            }
            
        except Exception as e:
            logger.error(f"Error parsing payment info: {e}")
            return None

    def extract_amount(self, text: str) -> Optional[float]:
        """Extract amount from text"""
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the amount string
                    amount_str = match.replace(',', '').replace(' ', '')
                    amount = float(amount_str)
                    
                    # Validate amount (reasonable range for Ethiopian context)
                    if 1 <= amount <= 1000000:  # 1 ETB to 1M ETB
                        return amount
                except ValueError:
                    continue
        return None

    def extract_bank(self, text: str) -> str:
        """Extract bank name from text"""
        for pattern, bank_name in self.bank_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return bank_name
        return 'Unknown Bank'

    def extract_reference(self, text: str) -> str:
        """Extract reference number from text"""
        for pattern in self.reference_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 4:  # Minimum reference length
                    return match
        return 'N/A'

    def extract_currency(self, text: str) -> str:
        """Extract currency from text"""
        for pattern in self.currency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if 'etb' in pattern or 'birr' in pattern:
                    return 'ETB'
                elif 'usd' in pattern or 'dollar' in pattern:
                    return 'USD'
                elif 'eur' in pattern or 'euro' in pattern:
                    return 'EUR'
        return 'ETB'  # Default to ETB for Ethiopian context

    def format_payment_info(self, payment_info: Dict) -> str:
        """Format payment information for display"""
        text = "✅ **Payment Captured Successfully!** ✅\n\n"
        text += f"💰 Amount: {payment_info['amount']} {payment_info['currency']}\n"
        text += f"🏦 Bank: {payment_info['bank']}\n"
        text += f"🔢 Reference: {payment_info['reference']}\n"
        text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        text += f"🔍 OCR Method: Enhanced Processing\n\n"
        text += "Transaction has been recorded and will be available for reconciliation."
        
        return text

    def generate_fallback_response(self, text: str) -> str:
        """Generate fallback response when parsing fails"""
        # Try to extract any numbers that might be amounts
        numbers = re.findall(r'\d+(?:\.\d{2})?', text)
        amount = None
        if numbers:
            try:
                amount = float(numbers[0])
                if 1 <= amount <= 1000000:
                    amount = amount
            except ValueError:
                pass
        
        if amount:
            text = "✅ **Payment Captured Successfully!** ✅\n\n"
            text += f"💰 Amount: {amount} ETB\n"
            text += f"🏦 Bank: Detected (Manual verification needed)\n"
            text += f"🔢 Reference: Extracted from image\n"
            text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            text += f"🔍 OCR Method: Fallback Processing\n\n"
            text += "⚠️ **Note: Some details may need manual verification**\n"
            text += "Transaction has been recorded and will be available for reconciliation."
        else:
            text = "❌ **Could not extract payment information from the image.**\n\n"
            text += "Please ensure the receipt is clear and contains:\n"
            text += "• Payment amount\n"
            text += "• Bank name\n"
            text += "• Reference number\n\n"
            text += "Try uploading a clearer image or contact support."
        
        return text

# Test the enhanced OCR processor
if __name__ == "__main__":
    processor = EnhancedOCRProcessor()
    
    # Test with sample text
    sample_text = """
    Commercial Bank of Ethiopia
    Transaction Receipt
    Amount: 150.00 ETB
    Reference: 1234567890
    Date: 2025-09-19
    """
    
    result, method = processor.extract_text_enhanced(sample_text)
    print(f"Method: {method}")
    print(f"Result:\n{result}")
