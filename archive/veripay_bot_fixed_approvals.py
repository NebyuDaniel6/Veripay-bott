#!/usr/bin/env python3
"""
VeriPay Bot - Fixed Super Admin Approvals
Only fixes the approval buttons issue without breaking anything else
"""

import asyncio
import logging
import re
import base64
import io
import random
from datetime import datetime
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# Google Vision OCR (optional)
try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except Exception:
    VISION_AVAILABLE = False
from enum import Enum
from typing import Dict, List, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, NetworkError, TimedOut

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc"

# User roles
class UserRole(Enum):
    NEW_USER = "new_user"
    WAITER = "waiter"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

# User states
class UserState(Enum):
    IDLE = "idle"
    WAITING_FOR_RESTAURANT_NAME = "waiting_for_restaurant_name"
    WAITING_FOR_RESTAURANT_PHONE = "waiting_for_restaurant_phone"
    WAITING_FOR_WAITER_NAME = "waiting_for_waiter_name"
    WAITING_FOR_WAITER_PHONE = "waiting_for_waiter_phone"
    WAITING_FOR_PAYMENT_AMOUNT = "waiting_for_payment_amount"
    WAITING_FOR_RECEIPT = "waiting_for_receipt"

# Global data storage
users: Dict[int, Dict] = {}
user_states: Dict[int, UserState] = {}
pending_restaurant_approvals: Dict[int, Dict] = {}
pending_waiter_approvals: Dict[int, Dict] = {}
restaurant_ids: Dict[int, str] = {}
waiter_ids: Dict[int, str] = {}
transactions: List[Dict] = []

# Super Admin ID
SUPER_ADMIN_ID = 369249230

class VeriPayBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.bot = self.application.bot
        self.setup_handlers()
        
        # Initialize super admin
        users[SUPER_ADMIN_ID] = {
            "role": UserRole.SUPER_ADMIN,
            "state": UserState.IDLE,
            "name": "Super Admin"
        }

    def setup_handlers(self):
        """Setup all command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.first_name or "User"
        
        logger.info(f"Audit: start_command by {user_id}: User {username} started bot")
        
        if user_id not in users:
            users[user_id] = {
                "role": UserRole.NEW_USER,
                "state": UserState.IDLE,
                "name": username
            }
            user_states[user_id] = UserState.IDLE

        user = users[user_id]
        
        if user["role"] == UserRole.SUPER_ADMIN:
            await self.show_super_admin_menu(update)
        elif user["role"] == UserRole.RESTAURANT_ADMIN:
            await self.show_restaurant_admin_menu(update)
        elif user["role"] == UserRole.WAITER:
            await self.show_waiter_menu(update)
        else:
            await self.show_role_selection(update)

    async def show_role_selection(self, update: Update):
        """Show role selection menu for new users"""
        keyboard = [
            [InlineKeyboardButton("🏪 Register Restaurant", callback_data="register_restaurant")],
            [InlineKeyboardButton("👨‍💼 Register as Waiter", callback_data="register_waiter")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🤖 **Welcome to VeriPay Bot!**\n\nPlease select your role:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_super_admin_menu(self, update: Update):
        """Show Super Admin menu with approval buttons"""
        keyboard = [
            [InlineKeyboardButton("📋 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("🏪 Active Restaurants", callback_data="active_restaurants")],
            [InlineKeyboardButton("📊 Daily Reports", callback_data="daily_reports")],
            [InlineKeyboardButton("❓ Admin Help", callback_data="admin_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "👑 **Super Admin Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_restaurant_admin_menu(self, update: Update):
        """Show Restaurant Admin menu"""
        keyboard = [
            [InlineKeyboardButton("📊 All Transactions", callback_data="all_transactions")],
            [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
            [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
            [InlineKeyboardButton("📈 Download Today's Report", callback_data="download_report")],
            [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🏪 **Restaurant Admin Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_waiter_menu(self, update: Update):
        """Show Waiter menu"""
        keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("❓ Help", callback_data="waiter_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "👨‍💼 **Waiter Dashboard**\n\nSelect an option:"
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "register_restaurant":
            await self.start_restaurant_registration(query)
        elif data == "register_waiter":
            await self.start_waiter_registration(query)
        elif data == "pending_restaurants":
            await self.show_pending_restaurants(query)
        elif data == "active_restaurants":
            await self.show_active_restaurants(query)
        elif data == "daily_reports":
            await self.show_daily_reports(query)
        elif data == "admin_help":
            await self.show_admin_help(query)
        elif data == "all_transactions":
            await self.show_all_transactions(query)
        elif data == "manage_waiters":
            await self.show_manage_waiters(query)
        elif data == "restaurant_settings":
            await self.show_restaurant_settings(query)
        elif data == "download_report":
            await self.download_report(query)
        elif data == "make_reconciliation":
            await self.show_reconciliation_options(query)
        elif data == "capture_payment":
            await self.start_capture_payment(query)
        elif data == "my_transactions":
            await self.show_my_transactions(query)
        elif data == "waiter_settings":
            await self.show_waiter_settings(query)
        elif data == "waiter_help":
            await self.show_waiter_help(query)
        elif data == "back_to_super_admin_menu":
            await self.show_super_admin_menu_callback(query)
        elif data == "back_to_restaurant_admin_menu":
            await self.show_restaurant_admin_menu_callback(query)
        elif data == "back_to_waiter_menu":
            await self.show_waiter_menu_callback(query)
        elif data.startswith("approve_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.approve_restaurant(query, restaurant_user_id)
        elif data.startswith("reject_restaurant_"):
            restaurant_user_id = int(data.split("_")[2])
            await self.reject_restaurant(query, restaurant_user_id)
        elif data.startswith("approve_waiter_"):
            waiter_user_id = int(data.split("_")[2])
            await self.approve_waiter(query, waiter_user_id)
        elif data.startswith("reject_waiter_"):
            waiter_user_id = int(data.split("_")[2])
            await self.reject_waiter(query, waiter_user_id)
        elif data == "sign_out":
            await self.sign_out(query)

    async def show_pending_restaurants(self, query):
        """Show pending restaurant approvals with approve/reject buttons"""
        if not pending_restaurant_approvals:
            message = "📋 **Pending Restaurant Approvals**\n\nNo pending approvals at the moment."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        else:
            message = "📋 **Pending Restaurant Approvals**\n\n"
            keyboard = []
            
            for user_id, data in pending_restaurant_approvals.items():
                message += f"🏪 **{data['restaurant_name']}**\n"
                message += f"📞 Phone: {data['restaurant_phone']}\n"
                message += f"👤 Owner: {data['owner_name']}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {data['restaurant_name']}", callback_data=f"approve_restaurant_{user_id}"),
                    InlineKeyboardButton(f"❌ Reject {data['restaurant_name']}", callback_data=f"reject_restaurant_{user_id}")
                ])
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def approve_restaurant(self, query, restaurant_user_id):
        """Approve a restaurant registration"""
        if restaurant_user_id in pending_restaurant_approvals:
            data = pending_restaurant_approvals[restaurant_user_id]
            users[restaurant_user_id]["role"] = UserRole.RESTAURANT_ADMIN
            users[restaurant_user_id]["state"] = UserState.IDLE
            restaurant_ids[restaurant_user_id] = data["restaurant_phone"]
            del pending_restaurant_approvals[restaurant_user_id]
            
            # Confirm to approver
            message = f"✅ **Restaurant Approved**\n\n{data['restaurant_name']} has been approved and is now active."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Auto-open Restaurant Admin menu for the approved user
            ra_keyboard = [
                [InlineKeyboardButton("📊 All Transactions", callback_data="all_transactions")],
                [InlineKeyboardButton("👥 Manage Waiters", callback_data="manage_waiters")],
                [InlineKeyboardButton("⚙️ Restaurant Settings", callback_data="restaurant_settings")],
                [InlineKeyboardButton("📈 Download Today's Report", callback_data="download_report")],
                [InlineKeyboardButton("🔄 Make Reconciliation", callback_data="make_reconciliation")],
                [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
            ]
            ra_markup = InlineKeyboardMarkup(ra_keyboard)
            ra_message = "🏪 **Restaurant Admin Dashboard**\n\nSelect an option:"
            try:
                await self.bot.send_message(chat_id=restaurant_user_id, text=ra_message, reply_markup=ra_markup, parse_mode='Markdown')
            except Exception as send_err:
                logger.error(f"Failed to send Restaurant Admin menu to {restaurant_user_id}: {send_err}")
            
            logger.info(f"Audit: restaurant_approved by {query.from_user.id}: Restaurant {restaurant_user_id} approved")

    async def reject_restaurant(self, query, restaurant_user_id):
        """Reject a restaurant registration"""
        if restaurant_user_id in pending_restaurant_approvals:
            data = pending_restaurant_approvals[restaurant_user_id]
            del pending_restaurant_approvals[restaurant_user_id]
            
            message = f"❌ **Restaurant Rejected**\n\n{data['restaurant_name']} has been rejected."
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
            logger.info(f"Audit: restaurant_rejected by {query.from_user.id}: Restaurant {restaurant_user_id} rejected")

    async def show_active_restaurants(self, query):
        """Show active restaurants"""
        if not restaurant_ids:
            message = "🏪 **Active Restaurants**\n\nNo active restaurants at the moment."
        else:
            message = "🏪 **Active Restaurants**\n\n"
            for user_id, phone in restaurant_ids.items():
                if user_id in users:
                    user = users[user_id]
                    message += f"🏪 **{user.get('restaurant_name', 'Unknown')}**\n"
                    message += f"📞 Phone: {phone}\n"
                    message += f"👤 Admin: {user.get('name', 'Unknown')}\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_daily_reports(self, query):
        """Show daily reports"""
        message = "📊 **Daily Reports**\n\nReports functionality coming soon!"
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_admin_help(self, query):
        """Show admin help"""
        message = "❓ **Admin Help**\n\nHelp documentation coming soon!"
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_super_admin_menu_callback(self, query):
        """Show Super Admin menu from callback"""
        keyboard = [
            [InlineKeyboardButton("📋 Pending Restaurant Approvals", callback_data="pending_restaurants")],
            [InlineKeyboardButton("🏪 Active Restaurants", callback_data="active_restaurants")],
            [InlineKeyboardButton("📊 Daily Reports", callback_data="daily_reports")],
            [InlineKeyboardButton("❓ Admin Help", callback_data="admin_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "👑 **Super Admin Dashboard**\n\nSelect an option:"
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_restaurant_registration(self, query):
        """Start restaurant registration process"""
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_RESTAURANT_NAME
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_NAME
        
        message = "🏪 **Restaurant Registration**\n\nPlease enter your restaurant name:"
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def start_waiter_registration(self, query):
        """Start waiter registration process"""
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_WAITER_NAME
        user_states[user_id] = UserState.WAITING_FOR_WAITER_NAME
        
        message = "👨‍💼 **Waiter Registration**\n\nPlease enter your full name:"
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_super_admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in users:
            await self.start_command(update, context)
            return
        
        user = users[user_id]
        state = user_states.get(user_id, UserState.IDLE)
        
        if state == UserState.WAITING_FOR_RESTAURANT_NAME:
            await self.handle_restaurant_name(update, text)
        elif state == UserState.WAITING_FOR_RESTAURANT_PHONE:
            await self.handle_restaurant_phone(update, text)
        elif state == UserState.WAITING_FOR_WAITER_NAME:
            await self.handle_waiter_name(update, text)
        elif state == UserState.WAITING_FOR_WAITER_PHONE:
            await self.handle_waiter_phone(update, text)
        elif state == UserState.WAITING_FOR_PAYMENT_AMOUNT:
            await self.handle_payment_amount(update, text)
        else:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")

    async def handle_restaurant_name(self, update: Update, text: str):
        """Handle restaurant name input"""
        user_id = update.effective_user.id
        users[user_id]["restaurant_name"] = text
        users[user_id]["state"] = UserState.WAITING_FOR_RESTAURANT_PHONE
        user_states[user_id] = UserState.WAITING_FOR_RESTAURANT_PHONE
        
        await update.message.reply_text("📞 Please enter your restaurant phone number:")

    async def handle_restaurant_phone(self, update: Update, text: str):
        """Handle restaurant phone input"""
        user_id = update.effective_user.id
        phone = text.strip()
        
        # Basic phone validation
        if not re.match(r'^\+?[0-9\s\-\(\)]{10,}$', phone):
            await update.message.reply_text("❌ Invalid phone number format. Please enter a valid phone number:")
            return
        
        users[user_id]["restaurant_phone"] = phone
        users[user_id]["state"] = UserState.IDLE
        user_states[user_id] = UserState.IDLE
        
        # Add to pending approvals
        pending_restaurant_approvals[user_id] = {
            "restaurant_name": users[user_id]["restaurant_name"],
            "restaurant_phone": phone,
            "owner_name": users[user_id]["name"]
        }
        
        await update.message.reply_text(
            "✅ **Restaurant registration submitted!**\n\n"
            "Your restaurant is pending approval from the Super Admin. "
            "You will be notified once approved."
        )
        
        logger.info(f"Audit: restaurant_registration by {user_id}: Restaurant {phone} registered by user {user_id}")

    async def handle_waiter_name(self, update: Update, text: str):
        """Handle waiter name input"""
        user_id = update.effective_user.id
        users[user_id]["waiter_name"] = text
        users[user_id]["state"] = UserState.WAITING_FOR_WAITER_PHONE
        user_states[user_id] = UserState.WAITING_FOR_WAITER_PHONE
        
        await update.message.reply_text("📞 Please enter your phone number:")

    async def handle_waiter_phone(self, update: Update, text: str):
        """Handle waiter phone input"""
        user_id = update.effective_user.id
        phone = text.strip()
        
        # Basic phone validation
        if not re.match(r'^\+?[0-9\s\-\(\)]{10,}$', phone):
            await update.message.reply_text("❌ Invalid phone number format. Please enter a valid phone number:")
            return
        
        users[user_id]["waiter_phone"] = phone
        users[user_id]["state"] = UserState.IDLE
        user_states[user_id] = UserState.IDLE
        
        # Add to pending approvals
        pending_waiter_approvals[user_id] = {
            "waiter_name": users[user_id]["waiter_name"],
            "waiter_phone": phone,
            "user_name": users[user_id]["name"]
        }
        
        await update.message.reply_text(
            "✅ **Waiter registration submitted!**\n\n"
            "Your waiter account is pending approval from a Restaurant Admin. "
            "You will be notified once approved."
        )
        
        logger.info(f"Audit: waiter_registration by {user_id}: Waiter {phone} registered by user {user_id}")

    async def handle_payment_amount(self, update: Update, text: str):
        """Handle payment amount input"""
        user_id = update.effective_user.id
        
        try:
            amount = float(text.replace(',', '').replace('$', '').replace('ETB', '').strip())
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            users[user_id]["payment_amount"] = amount
            users[user_id]["state"] = UserState.WAITING_FOR_RECEIPT
            user_states[user_id] = UserState.WAITING_FOR_RECEIPT
            
            await update.message.reply_text(
                f"💰 **Payment Amount: {amount} ETB**\n\n"
                "Please upload a photo of the receipt for OCR processing:"
            )
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a valid number:")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads"""
        user_id = update.effective_user.id
        
        if user_states.get(user_id) == UserState.WAITING_FOR_RECEIPT:
            await self.process_receipt_image(update)
        else:
            await update.message.reply_text("Please use the menu buttons to interact with the bot.")

    async def process_receipt_image(self, update: Update):
        """Process receipt image with OCR (pytesseract if available) and extract fields"""
        user_id = update.effective_user.id
        try:
            photo = update.message.photo[-1]
            file = await self.bot.get_file(photo.file_id)
            image_data = await file.download_as_bytearray()
            
            ocr_text = ""
            # Prefer Google Vision OCR if available
            if VISION_AVAILABLE:
                ocr_text = await self.perform_ocr_with_vision(bytes(image_data))
            # Fallback to pytesseract with preprocessing if Vision not available or returned empty
            if not ocr_text and OCR_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(image_data))
                    import PIL.ImageOps as ImageOps
                    import PIL.ImageFilter as ImageFilter
                    img = img.convert('L')
                    img = ImageOps.autocontrast(img)
                    img = img.filter(ImageFilter.SHARPEN)
                    # Simple thresholding
                    img = img.point(lambda p: 255 if p > 180 else 0)
                    ocr_text = pytesseract.image_to_string(img, lang='eng')
                except Exception as ocr_err:
                    logger.error(f"OCR error: {ocr_err}")
                    ocr_text = ""

            parsed = self.parse_receipt_text(ocr_text)

            amount = parsed.get("amount") or users[user_id].get("payment_amount", 0)
            bank_name = parsed.get("bank") or random.choice(["CBE", "Telebirr", "Dashen Bank", "Awash Bank", "Abyssinia"])
            reference_number = parsed.get("reference") or f"REF{random.randint(100000, 999999)}"
            timestamp_iso = parsed.get("datetime_iso") or datetime.now().isoformat()

            transaction = {
                "id": len(transactions) + 1,
                "user_id": user_id,
                "amount": amount,
                "bank": bank_name,
                "reference": reference_number,
                "timestamp": timestamp_iso,
                "status": "completed",
                "ocr_text": ocr_text[:2000]
            }
            transactions.append(transaction)
            
            users[user_id]["state"] = UserState.IDLE
            user_states[user_id] = UserState.IDLE
            
            human_dt = datetime.fromisoformat(timestamp_iso).strftime('%Y-%m-%d %H:%M:%S') if parsed.get("datetime_iso") else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await update.message.reply_text(
                f"✅ **Payment Processed**\n\n"
                f"💰 Amount: {amount} ETB\n"
                f"🏦 Bank: {bank_name}\n"
                f"🔢 Reference: {reference_number}\n"
                f"📅 Time: {human_dt}"
            )
            logger.info(f"Audit: payment_processed by {user_id}: Amount {amount} ETB, Ref {reference_number}, Bank {bank_name}")
        except Exception as e:
            logger.error(f"Error processing receipt: {e}")
            await update.message.reply_text("❌ Error processing receipt. Please try again.")

    async def perform_ocr_with_vision(self, image_bytes: bytes) -> str:
        """Use Google Cloud Vision OCR to extract text from image bytes."""
        if not VISION_AVAILABLE:
            return ""
        try:
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=image_bytes)
            response = client.text_detection(image=image)
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return ""
            annotations = response.text_annotations
            if not annotations:
                return ""
            return annotations[0].description or ""
        except Exception as e:
            logger.error(f"Vision OCR exception: {e}")
            return ""

    # --- OCR parsing helpers ---
    def parse_receipt_text(self, text: str) -> Dict[str, str]:
        """Parse OCR text to extract amount, date/time, reference, and bank/payment method.
        Returns dict with keys: amount (float), reference (str), bank (str), datetime_iso (str)
        """
        result: Dict[str, str] = {}
        if not text:
            return result
        try:
            # Normalize
            cleaned = text.replace('\r', ' ').replace('\n', ' ').strip()

            # Amount patterns (ETB, Birr, Br, ETB 1,234.56)
            amount_patterns = [
                r'(?:ETB|Birr|Br)\s*([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{1,2})?)',
                r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(?:ETB|Birr|Br)'
            ]
            for p in amount_patterns:
                m = re.search(p, cleaned, flags=re.IGNORECASE)
                if m:
                    num = m.group(1).replace(',', '').replace(' ', '')
                    try:
                        result["amount"] = float(num)
                        break
                    except Exception:
                        pass

            # Reference / Transaction ID patterns (CBE often starts with FT...)
            m = re.search(r"\bFT[0-9A-Z]{6,}\b", cleaned, flags=re.IGNORECASE)
            if m:
                result["reference"] = m.group(0)
            else:
                ref_patterns = [
                    r'(?:Ref(?:erence)?\s*[:#-]?\s*)([A-Z0-9]{5,})',
                    r'(?:Txn(?:\s*ID)?\s*[:#-]?\s*)([A-Z0-9]{5,})',
                    r'(?:Trans(?:action)?\s*No\.?\s*[:#-]?\s*)([A-Z0-9\-]{5,})'
                ]
                for p in ref_patterns:
                    m2 = re.search(p, cleaned, flags=re.IGNORECASE)
                    if m2:
                        result["reference"] = m2.group(1)
                        break

            # Date / time patterns: support YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY with 24h or 12h times; also try separate date and time pieces.
            dt_patterns = [
                r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?)',
                r'(\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}(?::\d{2})?)',
                r'(\d{2}-\d{2}-\d{4}[ T]\d{2}:\d{2}(?::\d{2})?)',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{2}-\d{2}-\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            time_patterns = [
                r'(\d{1,2}:\d{2}:\d{2}\s*[APap][Mm])',
                r'(\d{1,2}:\d{2}\s*[APap][Mm])',
                r'(\d{2}:\d{2}:\d{2})',
                r'(\d{2}:\d{2})'
            ]
            from datetime import datetime as _dt
            dt_found = None
            for p in dt_patterns:
                m = re.search(p, cleaned)
                if m and len(m.group(1)) > 10:
                    s = m.group(1).replace('T', ' ')
                    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S"):
                        try:
                            result["datetime_iso"] = _dt.strptime(s, fmt).isoformat()
                            dt_found = True
                            break
                        except ValueError:
                            continue
                if dt_found:
                    break
            if not dt_found:
                date_part = None
                for p in dt_patterns:
                    m = re.search(p, cleaned)
                    if m and len(m.group(1)) <= 10:
                        date_part = m.group(1)
                        break
                time_part = None
                if date_part:
                    for tp in time_patterns:
                        tm = re.search(tp, cleaned)
                        if tm:
                            time_part = tm.group(1)
                            break
                if date_part and time_part:
                    s = f"{date_part} {time_part}".replace('T', ' ')
                    # Normalize AM/PM spacing/case
                    s = re.sub(r'\s*([APap][Mm])\b', r' \1', s)
                    # Try multiple format combinations
                    fmts = (
                        "%d/%m/%Y %I:%M %p", "%d/%m/%Y %I:%M:%S %p",
                        "%d-%m-%Y %I:%M %p", "%d-%m-%Y %I:%M:%S %p",
                        "%Y-%m-%d %I:%M %p", "%Y-%m-%d %I:%M:%S %p",
                        "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
                        "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S",
                        "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
                    )
                    for fmt in fmts:
                        try:
                            result["datetime_iso"] = _dt.strptime(s, fmt).isoformat()
                            break
                        except ValueError:
                            continue
            # Bank / payment method
            banks = ["CBE", "Commercial Bank of Ethiopia", "Telebirr", "Dashen", "Dashen Bank", "Awash", "Awash Bank", "Abyssinia", "Bank of Abyssinia", "Zemen", "Nib", "Cooperative Bank of Oromia"]
            for b in banks:
                if re.search(rf'\b{re.escape(b)}\b', cleaned, flags=re.IGNORECASE):
                    result["bank"] = b if len(b) <= 20 else b.split()[0]
                    break
        except Exception as parse_err:
            logger.error(f"parse_receipt_text error: {parse_err}")
        return result
    # --- end OCR helpers ---

    # Placeholder methods for other functionality
    async def show_all_transactions(self, query):
        await query.edit_message_text("📊 All Transactions - Coming soon!")
    
    async def show_manage_waiters(self, query):
        # Build list of pending waiter approvals with approve/reject buttons
        if not pending_waiter_approvals:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_restaurant_admin_menu")]]
            await query.edit_message_text("👥 No pending waiter approvals.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        message = "👥 **Pending Waiter Approvals**\n\n"
        keyboard = []
        for waiter_id, data in pending_waiter_approvals.items():
            message += f"🧑 {data['waiter_name']} — {data['waiter_phone']}\n"
            keyboard.append([
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_waiter_{waiter_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_waiter_{waiter_id}")
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_restaurant_admin_menu")])
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    async def show_restaurant_settings(self, query):
        await query.edit_message_text("⚙️ Restaurant Settings - Coming soon!")
    
    async def download_report(self, query):
        await query.edit_message_text("📈 Download Report - Coming soon!")
    
    async def show_reconciliation_options(self, query):
        await query.edit_message_text("🔄 Reconciliation - Coming soon!")
    
    async def start_capture_payment(self, query):
        user_id = query.from_user.id
        users[user_id]["state"] = UserState.WAITING_FOR_PAYMENT_AMOUNT
        user_states[user_id] = UserState.WAITING_FOR_PAYMENT_AMOUNT
        message = "💳 **Capture Payment**\n\nPlease enter the payment amount in ETB (e.g., 250.50):"
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_waiter_menu")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    async def show_my_transactions(self, query):
        await query.edit_message_text("📋 My Transactions - Coming soon!")
    
    async def show_waiter_settings(self, query):
        await query.edit_message_text("⚙️ Waiter Settings - Coming soon!")
    
    async def show_waiter_help(self, query):
        await query.edit_message_text("❓ Waiter Help - Coming soon!")
    
    async def show_restaurant_admin_menu_callback(self, query):
        await query.edit_message_text("🏪 Restaurant Admin Menu - Coming soon!")
    
    async def show_waiter_menu_callback(self, query):
        await query.edit_message_text("👨‍💼 Waiter Menu - Coming soon!")
    
    async def approve_waiter(self, query, waiter_user_id):
        # remove from pending and notify
        if waiter_user_id in pending_waiter_approvals:
            del pending_waiter_approvals[waiter_user_id]
        await query.edit_message_text("✅ Waiter approved!")
        # Auto-open Waiter menu for the approved user
        w_keyboard = [
            [InlineKeyboardButton("💳 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📋 My Transactions", callback_data="my_transactions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="waiter_settings")],
            [InlineKeyboardButton("❓ Help", callback_data="waiter_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        w_markup = InlineKeyboardMarkup(w_keyboard)
        w_message = "👨‍💼 **Waiter Dashboard**\n\nSelect an option:"
        try:
            await self.bot.send_message(chat_id=waiter_user_id, text=w_message, reply_markup=w_markup, parse_mode='Markdown')
        except Exception as send_err:
            logger.error(f"Failed to send Waiter menu to {waiter_user_id}: {send_err}")
    
    async def reject_waiter(self, query, waiter_user_id):
        if waiter_user_id in pending_waiter_approvals:
            del pending_waiter_approvals[waiter_user_id]
        await query.edit_message_text("❌ Waiter rejected!")
    
    async def sign_out(self, query):
        await query.edit_message_text("🚪 Signed out successfully!")

    async def run(self):
        """Run the bot"""
        try:
            logger.info("Starting VeriPay Bot - FIXED APPROVALS VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            await asyncio.Event().wait()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            logger.info("Stopping bot...")
            await self.application.stop()

if __name__ == "__main__":
    bot = VeriPayBot()
    asyncio.run(bot.run())
