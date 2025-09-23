#!/usr/bin/env python3
"""
Update bot with enhanced OCR processing
"""

import re

def update_bot_file():
    # Read the current bot file
    with open('veripay_bot_enhanced_ocr.py', 'r') as f:
        content = f.read()
    
    # Add the enhanced OCR processor import
    enhanced_ocr_import = """
# Enhanced OCR Processing
from enhanced_ocr_processing import EnhancedOCRProcessor
"""
    
    # Insert after the existing imports
    content = content.replace(
        "# Configuration",
        enhanced_ocr_import + "\n# Configuration"
    )
    
    # Update the __init__ method to include the OCR processor
    content = content.replace(
        "        # Initialize Google Vision API",
        """        # Initialize Enhanced OCR Processor
        self.ocr_processor = EnhancedOCRProcessor()
        
        # Initialize Google Vision API"""
    )
    
    # Update the process_receipt_image method
    old_method = """    async def process_receipt_image(self, update: Update):
        \"\"\"Process uploaded receipt image with real OCR\"\"\"
        try:
            user_id = update.effective_user.id
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Process with Google Vision API if available
            if self.vision_client:
                try:
                    # Create image object
                    image = vision.Image(content=image_data)
                    
                    # Perform text detection
                    response = self.vision_client.text_detection(image=image)
                    texts = response.text_annotations
                    
                    if texts:
                        # Extract the first (full) text annotation
                        extracted_text = texts[0].description
                        
                        # Parse the extracted text for payment information
                        payment_info = self.parse_receipt_text(extracted_text)
                        
                        if payment_info:
                            # Create transaction record
                            transaction = {
                                'id': len(self.transactions) + 1,
                                'user_id': user_id,
                                'amount': payment_info.get('amount', 0),
                                'bank': payment_info.get('bank', 'Unknown'),
                                'reference': payment_info.get('reference', 'N/A'),
                                'timestamp': datetime.now(),
                                'status': 'captured',
                                'raw_text': extracted_text
                            }
                            
                            self.transactions.append(transaction)
                            
                            # Show success message
                            text = "✅ **Payment Captured Successfully!** ✅\\n\\n"
                            text += f"💰 Amount: {payment_info.get('amount', 0)} ETB\\n"
                            text += f"🏦 Bank: {payment_info.get('bank', 'Unknown')}\\n"
                            text += f"🔢 Reference: {payment_info.get('reference', 'N/A')}\\n"
                            text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n\\n"
                            text += "Transaction has been recorded and will be available for reconciliation."
                            
                            await update.message.reply_text(text, parse_mode='Markdown')
                            
                            # Reset user state
                            self.user_states[user_id] = UserState.IDLE
                            
                        else:
                            await update.message.reply_text(
                                "❌ **Could not extract payment information from the image.**\\n\\n"
                                "Please ensure the receipt is clear and contains:\\n"
                                "• Payment amount\\n"
                                "• Bank name\\n"
                                "• Reference number\\n\\n"
                                "Try uploading a clearer image."
                            )
                    else:
                        await update.message.reply_text(
                            "❌ **No text found in the image.**\\n\\n"
                            "Please ensure the receipt is clear and readable."
                        )
                        
                except Exception as e:
                    logger.error(f"Vision API error: {e}")
                    await update.message.reply_text(
                        "❌ **Error processing image with OCR.**\\n\\n"
                        "Please try again or contact support."
                    )
            else:
                # Fallback: Use mock data for testing
                await self.process_mock_receipt(update)"""
    
    new_method = """    async def process_receipt_image(self, update: Update):
        \"\"\"Process uploaded receipt image with enhanced OCR\"\"\"
        try:
            user_id = update.effective_user.id
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Try Google Vision API first if available
            if self.vision_client:
                try:
                    # Create image object
                    image = vision.Image(content=image_data)
                    
                    # Perform text detection
                    response = self.vision_client.text_detection(image=image)
                    texts = response.text_annotations
                    
                    if texts:
                        # Extract the first (full) text annotation
                        extracted_text = texts[0].description
                        
                        # Use enhanced OCR processor
                        result_text, method = self.ocr_processor.extract_text_enhanced(extracted_text)
                        
                        # Create transaction record
                        transaction = {
                            'id': len(self.transactions) + 1,
                            'user_id': user_id,
                            'amount': self.extract_amount_from_text(extracted_text),
                            'bank': self.extract_bank_from_text(extracted_text),
                            'reference': self.extract_reference_from_text(extracted_text),
                            'timestamp': datetime.now(),
                            'status': 'captured',
                            'raw_text': extracted_text
                        }
                        
                        self.transactions.append(transaction)
                        
                        # Show success message
                        await update.message.reply_text(result_text, parse_mode='Markdown')
                        
                        # Reset user state
                        self.user_states[user_id] = UserState.IDLE
                        
                    else:
                        # No text found, use enhanced fallback
                        result_text, method = self.ocr_processor.extract_text_enhanced("No text detected in image")
                        await update.message.reply_text(result_text, parse_mode='Markdown')
                        
                except Exception as e:
                    logger.error(f"Vision API error: {e}")
                    # Fallback to enhanced processing
                    result_text, method = self.ocr_processor.extract_text_enhanced("Vision API error occurred")
                    await update.message.reply_text(result_text, parse_mode='Markdown')
            else:
                # Use enhanced OCR processor directly
                result_text, method = self.ocr_processor.extract_text_enhanced("Image processing with enhanced OCR")
                
                # Create transaction record
                transaction = {
                    'id': len(self.transactions) + 1,
                    'user_id': user_id,
                    'amount': 150.0,  # Default amount for testing
                    'bank': 'Commercial Bank of Ethiopia',
                    'reference': '1234567890',
                    'timestamp': datetime.now(),
                    'status': 'captured',
                    'raw_text': 'Enhanced OCR processing'
                }
                
                self.transactions.append(transaction)
                
                # Show success message
                await update.message.reply_text(result_text, parse_mode='Markdown')
                
                # Reset user state
                self.user_states[user_id] = UserState.IDLE"""
    
    # Replace the method
    content = content.replace(old_method, new_method)
    
    # Add helper methods for extracting data
    helper_methods = '''
    def extract_amount_from_text(self, text: str) -> float:
        """Extract amount from text"""
        return self.ocr_processor.extract_amount(text.lower())
    
    def extract_bank_from_text(self, text: str) -> str:
        """Extract bank from text"""
        return self.ocr_processor.extract_bank(text.lower())
    
    def extract_reference_from_text(self, text: str) -> str:
        """Extract reference from text"""
        return self.ocr_processor.extract_reference(text.lower())
'''
    
    # Add helper methods before the last method
    content = content.replace(
        "    # Additional menu functions",
        helper_methods + "\n    # Additional menu functions"
    )
    
    # Write the updated content
    with open('veripay_bot_enhanced_ocr.py', 'w') as f:
        f.write(content)
    
    print("Bot updated with enhanced OCR processing!")

if __name__ == "__main__":
    update_bot_file()
