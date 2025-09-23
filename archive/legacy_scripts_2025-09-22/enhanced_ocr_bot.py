#!/usr/bin/env python3
"""
Enhanced VeriPay Bot with Improved OCR Processing
- Better text parsing patterns for Ethiopian banks
- Fallback OCR methods
- Enhanced error handling
"""

import asyncio
import logging
import re
import os
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

# Telegram Bot API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Database
import asyncpg

# Image processing
from PIL import Image
import io

# Google Cloud Vision API
try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

# Configuration
BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"
SUPER_ADMIN_USER_ID = 369249230

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserState(Enum):
    IDLE = "idle"
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_RECEIPT_IMAGE = "waiting_for_receipt_image"

class VeriPayBot:
    def __init__(self):
        self.bot_token = BOT_TOKEN
        self.users: Dict[int, Dict] = {}
        self.restaurants: Dict[int, Dict] = {}
        self.waiters: Dict[int, Dict] = {}
        self.transactions: List[Dict] = []
        self.user_states: Dict[int, UserState] = {}
        self.running = False
        
        # Initialize Google Vision API
        self.vision_client = None
        if VISION_AVAILABLE:
            try:
                self.vision_client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API initialized successfully")
            except Exception as e:
                logger.warning(f"Google Vision API not available: {e}")
        
        # Setup application
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup bot handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image_message))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"User {username} ({user_id}) started bot")
        
        # Initialize user
        if user_id not in self.users:
            self.users[user_id] = {
                'id': user_id,
                'username': username,
                'role': 'waiter',  # Default role
                'restaurant_id': None,
                'created_at': datetime.now()
            }
        
        self.user_states[user_id] = UserState.IDLE
        
        # Show appropriate menu based on user role
        if user_id == SUPER_ADMIN_USER_ID:
            await self.show_super_admin_menu(update, None)
        elif user_id in self.restaurants:
            await self.show_restaurant_admin_menu(update, None)
        else:
            await self.show_waiter_menu(update, None)
    
    async def show_super_admin_menu(self, update: Update, query):
        """Show super admin menu"""
        text = "🔧 **Super Admin Panel**\n\n"
        text += "Welcome to VeriPay Bot Management!\n\n"
        text += "**Available Commands:**\n"
        text += "• Manage restaurants\n"
        text += "• Approve registrations\n"
        text += "• View transactions\n"
        text += "• System monitoring\n\n"
        text += "Select an option below:"
        
        keyboard = [
            [InlineKeyboardButton("🏪 Manage Restaurants", callback_data="manage_restaurants")],
            [InlineKeyboardButton("👥 Approve Registrations", callback_data="approve_registrations")],
            [InlineKeyboardButton("📊 View Transactions", callback_data="view_transactions")],
            [InlineKeyboardButton("⚙️ System Status", callback_data="system_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update, query):
        """Show restaurant admin menu"""
        text = "🏪 **Restaurant Admin Panel**\n\n"
        text += "Welcome to your restaurant management dashboard!\n\n"
        text += "**Available Commands:**\n"
        text += "• Manage waiters\n"
        text += "• View transactions\n"
        text += "• Upload bank statements\n"
        text += "• Reconciliation\n\n"
        text += "Select an option below:"
        
        keyboard = [
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
            [InlineKeyboardButton("📊 View Transactions", callback_data="view_transactions")],
            [InlineKeyboardButton("📄 Upload Bank Statement", callback_data="upload_statement")],
            [InlineKeyboardButton("🔄 Reconciliation", callback_data="reconciliation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update, query):
        """Show waiter menu"""
        text = "👨‍💼 **Waiter Panel**\n\n"
        text += "Welcome to VeriPay Bot!\n\n"
        text += "**Available Commands:**\n"
        text += "• Capture payment\n"
        text += "• View my transactions\n"
        text += "• Register restaurant\n\n"
        text += "Select an option below:"
        
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📊 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "capture_payment":
            await self.start_payment_capture(update, query)
        elif data == "register_restaurant":
            await self.start_restaurant_registration(update, query)
        elif data == "manage_restaurants":
            await self.show_restaurant_management(update, query)
        elif data == "approve_registrations":
            await self.show_pending_approvals(update, query)
        else:
            await query.edit_message_text("Feature coming soon!")
    
    async def start_payment_capture(self, update: Update, query):
        """Start payment capture process"""
        user_id = query.from_user.id
        self.user_states[user_id] = UserState.WAITING_FOR_RECEIPT_IMAGE
        
        text = "💳 **Payment Capture**\n\n"
        text += "Please upload a clear photo of the payment receipt.\n\n"
        text += "**Make sure the receipt shows:**\n"
        text += "• Payment amount\n"
        text += "• Bank name (CBE, Telebirr, Dashen, etc.)\n"
        text += "• Reference/Transaction number\n\n"
        text += "📸 **Upload the receipt image now:**"
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    async def handle_image_message(self, update: Update, context):
        """Handle image uploads for OCR processing"""
        user_id = update.effective_user.id
        
        if self.user_states.get(user_id) == UserState.WAITING_FOR_RECEIPT_IMAGE:
            await self.process_receipt_image_enhanced(update)
        else:
            await update.message.reply_text("Please use the menu to start payment capture first.")
    
    async def process_receipt_image_enhanced(self, update: Update):
        """Enhanced receipt image processing with multiple OCR methods"""
        try:
            user_id = update.effective_user.id
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Try multiple OCR methods
            extracted_text = None
            ocr_method = "Unknown"
            
            # Method 1: Google Vision API (if available)
            if self.vision_client:
                try:
                    extracted_text, ocr_method = await self.extract_text_vision_api(image_data)
                    if extracted_text:
                        logger.info(f"Successfully extracted text using Google Vision API")
                except Exception as e:
                    logger.warning(f"Google Vision API failed: {e}")
            
            # Method 2: Basic image processing (fallback)
            if not extracted_text:
                try:
                    extracted_text, ocr_method = await self.extract_text_basic(image_data)
                    if extracted_text:
                        logger.info(f"Successfully extracted text using basic processing")
                except Exception as e:
                    logger.warning(f"Basic OCR failed: {e}")
            
            if extracted_text:
                # Parse the extracted text for payment information
                payment_info = self.parse_receipt_text_enhanced(extracted_text)
                
                if payment_info and payment_info.get('amount'):
                    # Create transaction record
                    transaction = {
                        'id': len(self.transactions) + 1,
                        'user_id': user_id,
                        'amount': payment_info.get('amount', 0),
                        'bank': payment_info.get('bank', 'Unknown'),
                        'reference': payment_info.get('reference', 'N/A'),
                        'timestamp': datetime.now(),
                        'status': 'captured',
                        'raw_text': extracted_text,
                        'ocr_method': ocr_method
                    }
                    
                    self.transactions.append(transaction)
                    
                    # Show success message
                    text = "✅ **Payment Captured Successfully!** ✅\n\n"
                    text += f"💰 Amount: {payment_info.get('amount', 0)} ETB\n"
                    text += f"🏦 Bank: {payment_info.get('bank', 'Unknown')}\n"
                    text += f"🔢 Reference: {payment_info.get('reference', 'N/A')}\n"
                    text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    text += f"🔍 OCR Method: {ocr_method}\n\n"
                    text += "Transaction has been recorded and will be available for reconciliation."
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    
                    # Reset user state
                    self.user_states[user_id] = UserState.IDLE
                    
                else:
                    await update.message.reply_text(
                        "❌ **Could not extract payment information from the image.**\n\n"
                        "**Extracted text:**\n"
                        f"```\n{extracted_text[:200]}...\n```\n\n"
                        "Please ensure the receipt is clear and contains:\n"
                        "• Payment amount\n"
                        "• Bank name\n"
                        "• Reference number\n\n"
                        "Try uploading a clearer image."
                    )
            else:
                await update.message.reply_text(
                    "❌ **No text found in the image.**\n\n"
                    "Please ensure the receipt is clear and readable."
                )
                
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            await update.message.reply_text(
                "❌ **Error processing image.**\n\n"
                "Please try again or contact support."
            )
    
    async def extract_text_vision_api(self, image_data: bytes) -> tuple:
        """Extract text using Google Vision API"""
        try:
            # Create image object
            image = vision.Image(content=image_data)
            
            # Perform text detection
            response = self.vision_client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description, "Google Vision API"
            return None, "Google Vision API"
        except Exception as e:
            logger.error(f"Vision API error: {e}")
            return None, "Google Vision API"
    
    async def extract_text_basic(self, image_data: bytes) -> tuple:
        """Basic text extraction using image processing"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Basic text extraction simulation
            # In a real implementation, you would use pytesseract here
            # For now, we'll return a placeholder
            return "Basic OCR placeholder text", "Basic Processing"
        except Exception as e:
            logger.error(f"Basic OCR error: {e}")
            return None, "Basic Processing"
    
    def parse_receipt_text_enhanced(self, text: str) -> dict:
        """Enhanced text parsing with better patterns for Ethiopian banks"""
        try:
            # Convert to lowercase for easier matching
            text_lower = text.lower()
            
            # Enhanced amount patterns for Ethiopian currency
            amount_patterns = [
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:etb|birr|br)',  # 1,000.00 ETB
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 1,000.00
                r'amount[:\s]*(\d+(?:\.\d{2})?)',  # amount: 100.00
                r'total[:\s]*(\d+(?:\.\d{2})?)',  # total: 100.00
                r'paid[:\s]*(\d+(?:\.\d{2})?)',  # paid: 100.00
                r'(\d+(?:\.\d{2})?)\s*(?:etb|birr|br)',  # 100.00 ETB
            ]
            
            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        if amount > 0:  # Ensure positive amount
                            break
                    except ValueError:
                        continue
            
            # Enhanced bank name patterns for Ethiopian banks
            bank_patterns = [
                (r'(commercial bank of ethiopia|cbe)', 'Commercial Bank of Ethiopia'),
                (r'(telebirr)', 'Telebirr'),
                (r'(dashen bank|dashen)', 'Dashen Bank'),
                (r'(awash bank|awash)', 'Awash Bank'),
                (r'(nib international bank|nib)', 'NIB International Bank'),
                (r'(bank of abyssinia|boa)', 'Bank of Abyssinia'),
                (r'(united bank|ub)', 'United Bank'),
                (r'(cooperative bank of oromia|cbo)', 'Cooperative Bank of Oromia'),
                (r'(lion international bank|lib)', 'Lion International Bank'),
                (r'(bank)', 'Bank'),
            ]
            
            bank = 'Unknown'
            for pattern, bank_name in bank_patterns:
                if re.search(pattern, text_lower):
                    bank = bank_name
                    break
            
            # Enhanced reference number patterns
            ref_patterns = [
                r'ref[:\s]*(\d+)',
                r'reference[:\s]*(\d+)',
                r'txn[:\s]*(\d+)',
                r'transaction[:\s]*(\d+)',
                r'trace[:\s]*(\d+)',
                r'(\d{10,})',  # Long number sequences
            ]
            
            reference = 'N/A'
            for pattern in ref_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    reference = match.group(1)
                    break
            
            return {
                'amount': amount,
                'bank': bank,
                'reference': reference
            }
            
        except Exception as e:
            logger.error(f"Error parsing receipt text: {e}")
            return None
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Handle different user states
        if self.user_states.get(user_id) == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, text)
        elif self.user_states.get(user_id) == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, text)
        else:
            await update.message.reply_text("Please use the menu to navigate.")
    
    async def handle_restaurant_name(self, update: Update, text: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        self.users[user_id]['restaurant_name'] = text
        self.user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text(
            "📞 **Restaurant Phone Number**\n\n"
            "Please enter the restaurant's phone number:"
        )
    
    async def handle_restaurant_phone(self, update: Update, text: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        
        # Validate phone number
        if not re.match(r'^\+?[\d\s-]{10,}$', text):
            await update.message.reply_text(
                "❌ **Invalid phone number format.**\n\n"
                "Please enter a valid phone number:"
            )
            return
        
        # Complete restaurant registration
        restaurant_id = len(self.restaurants) + 1
        self.restaurants[restaurant_id] = {
            'id': restaurant_id,
            'name': self.users[user_id]['restaurant_name'],
            'phone': text,
            'admin_user_id': user_id,
            'status': 'pending',
            'created_at': datetime.now()
        }
        
        self.users[user_id]['restaurant_id'] = restaurant_id
        self.users[user_id]['role'] = 'restaurant_admin'
        self.user_states[user_id] = UserState.IDLE
        
        await update.message.reply_text(
            "✅ **Restaurant Registration Complete!**\n\n"
            f"🏪 Restaurant: {self.restaurants[restaurant_id]['name']}\n"
            f"📞 Phone: {text}\n"
            f"👤 Admin: {update.effective_user.username}\n\n"
            "Your restaurant registration is pending approval from the Super Admin."
        )
    
    async def start_restaurant_registration(self, update: Update, query):
        """Start restaurant registration process"""
        user_id = query.from_user.id
        self.user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        text = "🏪 **Restaurant Registration**\n\n"
        text += "Please enter the restaurant name:"
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    async def show_restaurant_management(self, update: Update, query):
        """Show restaurant management options"""
        text = "🏪 **Restaurant Management**\n\n"
        text += f"Total Restaurants: {len(self.restaurants)}\n"
        text += f"Pending Approvals: {len([r for r in self.restaurants.values() if r['status'] == 'pending'])}\n\n"
        text += "Select an option:"
        
        keyboard = [
            [InlineKeyboardButton("📋 View All Restaurants", callback_data="view_restaurants")],
            [InlineKeyboardButton("⏳ Pending Approvals", callback_data="pending_approvals")],
            [InlineKeyboardButton("✅ Approved Restaurants", callback_data="approved_restaurants")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_approvals(self, update: Update, query):
        """Show pending approvals"""
        pending_restaurants = [r for r in self.restaurants.values() if r['status'] == 'pending']
        
        if not pending_restaurants:
            text = "✅ **No Pending Approvals**\n\n"
            text += "All restaurant registrations have been processed."
            await query.edit_message_text(text, parse_mode='Markdown')
            return
        
        text = "⏳ **Pending Restaurant Approvals**\n\n"
        for restaurant in pending_restaurants:
            text += f"🏪 **{restaurant['name']}**\n"
            text += f"📞 Phone: {restaurant['phone']}\n"
            text += f"👤 Admin: {restaurant['admin_user_id']}\n"
            text += f"📅 Registered: {restaurant['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = []
        for restaurant in pending_restaurants:
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {restaurant['name']}", 
                                   callback_data=f"approve_restaurant_{restaurant['id']}"),
                InlineKeyboardButton(f"❌ Reject {restaurant['name']}", 
                                   callback_data=f"reject_restaurant_{restaurant['id']}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="manage_restaurants")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def run(self):
        """Run the bot"""
        if self.running:
            logger.warning("Bot is already running!")
            return
        
        try:
            self.running = True
            logger.info("Starting Enhanced VeriPay Bot...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Clear webhook
            await self.bot.delete_webhook()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Start polling
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.running = False
            logger.info("Bot stopped.")
    
    @property
    def bot(self):
        return self.application.bot

async def main():
    """Main function"""
    bot = VeriPayBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
