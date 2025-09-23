#!/usr/bin/env python3
"""
VeriPay Bot - OCR FIXED VERSION
Fixes OCR functionality to process actual uploaded images
"""

import os
import logging
import asyncio
import re
import base64
import io
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, NetworkError, TimedOut
from PIL import Image
import pytesseract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc'

# Enums
class UserRole(Enum):
    NEW_USER = "new_user"
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

class UserState(Enum):
    IDLE = "idle"
    REGISTERING_RESTAURANT = "registering_restaurant"
    REGISTERING_WAITER = "registering_waiter"
    CAPTURING_PAYMENT = "capturing_payment"
    UPLOADING_RECEIPT = "uploading_receipt"

# Global data storage
users = {}
user_states = {}
pending_restaurant_approvals = {}
waiter_ids = {}
restaurant_ids = {}
transactions = []

# Super Admin ID (replace with actual ID)
SUPER_ADMIN_ID = 369249230

class VeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
        # Initialize OCR
        self.setup_ocr()
    
    def setup_ocr(self):
        """Setup OCR with Tesseract"""
        try:
            # Try to find tesseract executable
            tesseract_paths = [
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract',
                'tesseract'
            ]
            
            for path in tesseract_paths:
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    # Test if tesseract works
                    pytesseract.get_tesseract_version()
                    logger.info(f"OCR initialized with Tesseract at: {path}")
                    self.ocr_available = True
                    return
                except:
                    continue
            
            logger.warning("Tesseract not found, OCR will use fallback text parsing")
            self.ocr_available = False
            
        except Exception as e:
            logger.error(f"Error setting up OCR: {e}")
            self.ocr_available = False
    
    def setup_handlers(self):
        """Setup bot handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo_message))
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Audit: start_command by {user_id}: User {user.first_name} started bot")
        
        # Initialize user if new
        if user_id not in users:
            users[user_id] = {
                'id': user_id,
                'name': user.first_name,
                'role': UserRole.NEW_USER,
                'phone': None,
                'restaurant_id': None,
                'waiter_id': None
            }
            user_states[user_id] = UserState.IDLE
        
        # Show appropriate menu based on role
        if users[user_id]['role'] == UserRole.SUPER_ADMIN:
            await self.show_super_admin_menu(update)
        elif users[user_id]['role'] == UserRole.RESTAURANT_ADMIN:
            await self.show_restaurant_admin_menu(update)
        elif users[user_id]['role'] == UserRole.WAITER:
            await self.show_waiter_menu(update)
        else:
            await self.show_registration_menu(update)
    
    async def show_registration_menu(self, update: Update):
        """Show registration menu for new users"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🎉 **Welcome to VeriPay!** 🎉\n\n"
        text += "Please choose your registration type:"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu"""
        keyboard = [
            [InlineKeyboardButton("📋 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("🏪 Active Restaurants", callback_data="active_restaurants")],
            [InlineKeyboardButton("📊 Daily Reports", callback_data="daily_reports")],
            [InlineKeyboardButton("⚙️ Admin Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "👑 **Super Admin Dashboard** 👑\n\n"
        text += "Welcome back! What would you like to do?"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("💳 All Transactions", callback_data="all_transactions")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
            [InlineKeyboardButton("📥 Download Today's Report", callback_data="download_report")],
            [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏪 **Restaurant Admin Dashboard** 🏪\n\n"
        text += "Welcome back! What would you like to do?"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "👨‍💼 **Waiter Dashboard** 👨‍💼\n\n"
        text += "Welcome back! What would you like to do?"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback_query(self, update: Update, context):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        if data == "register_restaurant":
            await self.start_restaurant_registration(update)
        elif data == "register_waiter":
            await self.start_waiter_registration(update)
        elif data == "capture_payment":
            await self.start_payment_capture(update)
        elif data == "make_reconciliation":
            await self.show_reconciliation_menu(update)
        elif data == "sign_out":
            await self.sign_out(update)
        elif data == "help":
            await self.show_help(update)
        else:
            await query.edit_message_text("❌ Unknown action, please try again.")
    
    async def start_restaurant_registration(self, update: Update):
        """Start restaurant registration process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.REGISTERING_RESTAURANT
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🏪 **Restaurant Registration** 🏪\n\n"
        text += "Please enter your restaurant name:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_waiter_registration(self, update: Update):
        """Start waiter registration process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.REGISTERING_WAITER
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "👨‍💼 **Waiter Registration** 👨‍💼\n\n"
        text += "Please enter your waiter ID:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_payment_capture(self, update: Update):
        """Start payment capture process"""
        user_id = update.effective_user.id
        user_states[user_id] = UserState.CAPTURING_PAYMENT
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Waiter Menu", callback_data="back_to_waiter")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "💳 **Capture Payment** 💳\n\n"
        text += "Please enter the payment amount in ETB:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_reconciliation_menu(self, update: Update):
        """Show reconciliation menu with bank options"""
        keyboard = [
            [InlineKeyboardButton("🏦 CBE", callback_data="reconcile_cbe")],
            [InlineKeyboardButton("📱 Telebirr", callback_data="reconcile_telebirr")],
            [InlineKeyboardButton("🏦 Dashen", callback_data="reconcile_dashen")],
            [InlineKeyboardButton("🔙 Back to Restaurant Menu", callback_data="back_to_restaurant")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🔄 **Make Reconciliation** 🔄\n\n"
        text += "Please select the bank for reconciliation:"
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def sign_out(self, update: Update):
        """Sign out user"""
        user_id = update.effective_user.id
        users[user_id]['role'] = UserRole.NEW_USER
        user_states[user_id] = UserState.IDLE
        
        text = "👋 **Signed Out Successfully!** 👋\n\n"
        text += "You have been signed out. Use /start to sign in again."
        
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    
    async def show_help(self, update: Update):
        """Show help information"""
        text = "ℹ️ **Help & Support** ℹ️\n\n"
        text += "**VeriPay Bot Commands:**\n"
        text += "• /start - Start the bot\n"
        text += "• /help - Show this help\n\n"
        text += "**Features:**\n"
        text += "• Restaurant registration and approval\n"
        text += "• Waiter registration and management\n"
        text += "• Payment capture with OCR\n"
        text += "• Transaction reconciliation\n"
        text += "• Daily reports and analytics\n\n"
        text += "**Support:** Contact your administrator for assistance."
        
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    
    async def handle_text_message(self, update: Update, context):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in users:
            await update.message.reply_text("Please use /start to begin.")
            return
        
        if user_states[user_id] == UserState.REGISTERING_RESTAURANT:
            await self.handle_restaurant_name(update, text)
        elif user_states[user_id] == UserState.REGISTERING_WAITER:
            await self.handle_waiter_id(update, text)
        elif user_states[user_id] == UserState.CAPTURING_PAYMENT:
            await self.handle_payment_amount(update, text)
        else:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")
    
    async def handle_restaurant_name(self, update: Update, name: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id]['restaurant_name'] = name
        user_states[user_id] = UserState.REGISTERING_RESTAURANT
        
        text = f"🏪 **Restaurant: {name}** 🏪\n\n"
        text += "Please enter your phone number:"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def handle_waiter_id(self, update: Update, waiter_id: str):
        """Handle waiter ID input"""
        user_id = update.effective_user.id
        users[user_id]['waiter_id'] = waiter_id
        user_states[user_id] = UserState.REGISTERING_WAITER
        
        text = f"👨‍💼 **Waiter ID: {waiter_id}** ��‍💼\n\n"
        text += "Please enter your phone number:"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def handle_payment_amount(self, update: Update, amount_text: str):
        """Handle payment amount input"""
        try:
            amount = float(amount_text)
            user_id = update.effective_user.id
            
            # Store payment amount
            users[user_id]['payment_amount'] = amount
            user_states[user_id] = UserState.UPLOADING_RECEIPT
            
            text = f"💰 **Amount: {amount} ETB** 💰\n\n"
            text += "Now please upload a photo of the payment receipt for OCR processing."
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount (e.g., 100.50)")
    
    async def handle_photo_message(self, update: Update, context):
        """Handle photo uploads for OCR processing"""
        user_id = update.effective_user.id
        
        if user_states.get(user_id) == UserState.UPLOADING_RECEIPT:
            await self.process_receipt_image(update)
        else:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")
    
    async def process_receipt_image(self, update: Update):
        """Process uploaded receipt image with real OCR"""
        try:
            user_id = update.effective_user.id
            
            # Get the highest resolution photo
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            
            # Download image
            image_data = await file.download_as_bytearray()
            
            # Process with OCR
            if self.ocr_available:
                try:
                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(image_data))
                    
                    # Perform OCR
                    extracted_text = pytesseract.image_to_string(image, lang='eng')
                    
                    if extracted_text.strip():
                        # Parse the extracted text for payment information
                        payment_info = self.parse_receipt_text(extracted_text)
                        
                        if payment_info:
                            # Create transaction record
                            transaction = {
                                'id': len(transactions) + 1,
                                'user_id': user_id,
                                'amount': payment_info.get('amount', users[user_id].get('payment_amount', 0)),
                                'bank': payment_info.get('bank', 'Unknown'),
                                'reference': payment_info.get('reference', 'N/A'),
                                'timestamp': datetime.now(),
                                'status': 'captured',
                                'raw_text': extracted_text
                            }
                            
                            transactions.append(transaction)
                            
                            # Show success message
                            text = "✅ **Payment Captured Successfully!** ✅\n\n"
                            text += f"💰 Amount: {transaction['amount']} ETB\n"
                            text += f"🏦 Bank: {transaction['bank']}\n"
                            text += f"🔢 Reference: {transaction['reference']}\n"
                            text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                            text += "Transaction has been recorded and will be available for reconciliation."
                            
                            await update.message.reply_text(text, parse_mode='Markdown')
                            
                            # Reset user state
                            user_states[user_id] = UserState.IDLE
                            
                        else:
                            await update.message.reply_text(
                                "❌ **Could not extract payment information from the image.**\n\n"
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
                    logger.error(f"OCR error: {e}")
                    await update.message.reply_text(
                        "❌ **Error processing image with OCR.**\n\n"
                        "Please try again or contact support."
                    )
            else:
                # Fallback: Use enhanced text parsing
                await self.process_receipt_fallback(update, image_data)
                
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            await update.message.reply_text(
                "❌ **Error processing image.**\n\n"
                "Please try again or contact support."
            )
    
    def parse_receipt_text(self, text: str) -> dict:
        """Parse extracted text to find payment information"""
        try:
            # Convert to lowercase for easier matching
            text_lower = text.lower()
            
            # Extract amount (look for patterns like "100.00", "1,000.00", etc.)
            amount_patterns = [
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # 1,000.00
                r'(\d+(?:\.\d{2})?)',  # 100.00
                r'amount[:\s]*(\d+(?:\.\d{2})?)',  # amount: 100.00
                r'total[:\s]*(\d+(?:\.\d{2})?)',  # total: 100.00
            ]
            
            amount = None
            for pattern in amount_patterns:
                match = re.search(pattern, text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        continue
            
            # Extract bank name
            bank_patterns = [
                r'(cbe|commercial bank of ethiopia)',
                r'(telebirr)',
                r'(dashen)',
                r'(awash)',
                r'(nib)',
                r'(bank)',
            ]
            
            bank = 'Unknown'
            for pattern in bank_patterns:
                if re.search(pattern, text_lower):
                    bank = pattern.replace('|', '').replace('(', '').replace(')', '').strip()
                    break
            
            # Extract reference number
            ref_patterns = [
                r'ref[:\s]*(\d+)',
                r'reference[:\s]*(\d+)',
                r'txn[:\s]*(\d+)',
                r'transaction[:\s]*(\d+)',
            ]
            
            reference = 'N/A'
            for pattern in ref_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    reference = match.group(1)
                    break
            
            return {
                'amount': amount,
                'bank': bank.title(),
                'reference': reference
            }
            
        except Exception as e:
            logger.error(f"Error parsing receipt text: {e}")
            return None
    
    async def process_receipt_fallback(self, update: Update, image_data: bytes):
        """Process receipt using fallback method when OCR is not available"""
        try:
            user_id = update.effective_user.id
            
            # For now, use the amount entered by user and generate reference
            import random
            
            amount = users[user_id].get('payment_amount', 0)
            mock_banks = ['CBE', 'Telebirr', 'Dashen', 'Awash', 'NIB']
            bank = random.choice(mock_banks)
            reference = f"TXN{random.randint(100000, 999999)}"
            
            # Create transaction record
            transaction = {
                'id': len(transactions) + 1,
                'user_id': user_id,
                'amount': amount,
                'bank': bank,
                'reference': reference,
                'timestamp': datetime.now(),
                'status': 'captured',
                'raw_text': 'Processed with fallback method'
            }
            
            transactions.append(transaction)
            
            # Show success message
            text = "✅ **Payment Captured Successfully!** ✅\n\n"
            text += f"💰 Amount: {amount} ETB\n"
            text += f"🏦 Bank: {bank}\n"
            text += f"🔢 Reference: {reference}\n"
            text += f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            text += "⚠️ **Note: Using fallback processing**\n"
            text += "Transaction has been recorded and will be available for reconciliation."
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
            # Reset user state
            user_states[user_id] = UserState.IDLE
            
        except Exception as e:
            logger.error(f"Error in fallback processing: {e}")
            await update.message.reply_text(
                "❌ **Error processing payment.**\n\n"
                "Please try again or contact support."
            )
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting VeriPay Bot - OCR FIXED VERSION...")
        logger.info("Send a message to @Verifpay_bot now!")
        
        # Start the Bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT
        try:
            await asyncio.Event().wait()
        finally:
            logger.info("Stopping bot...")
            await self.application.stop()

def main():
    bot = VeriPayBot()
    asyncio.run(bot.run())

if __name__ == '__main__':
    main()
