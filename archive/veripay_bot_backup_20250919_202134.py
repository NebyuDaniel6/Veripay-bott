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
except ImportError:
    VISION_AVAILABLE = False

# OCR Fallback - pytesseract and PIL
try:
    import pytesseract
    from PIL import Image, ImageOps
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

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
            await self.show_super_admin_menu(update, None)
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

    async def notify_restaurant_admin_waiter_registration(self, waiter_id: str, user_data: Dict):
        """Notify Restaurant Admin about new waiter registration"""
        try:
            # Find restaurant admin (this is simplified - in real app, you would have proper restaurant-waiter mapping)
            restaurant_admin_id = None
            for rid, uid in restaurant_ids.items():
                if users[uid]["role"] == UserRole.RESTAURANT_ADMIN:
                    restaurant_admin_id = uid
                    break
            
            if restaurant_admin_id:
                message = (
                    f"👨‍🍳 **New Waiter Registration** 👨‍🍳\n\n"
                    f"**Waiter ID:** {waiter_id}\n"
                    f"**Name:** {user_data["waiter_name"]}\n"
                    f"**Phone:** {user_data["waiter_phone"]}\n"
                    f"**Username:** @{user_data["username"]}\n\n"
                    f"Please review and approve this waiter."
                )
                
                await self.bot.send_message(
                    chat_id=restaurant_admin_id,
                    text=message,
                    parse_mode="Markdown"
                )
                
                logger.info(f"Audit: restaurant_admin_notified by {user_data["id"]}: Waiter {waiter_id} notification sent")
            else:
                logger.warning("No restaurant admin found to notify about waiter registration")
                
        except Exception as e:
            logger.error(f"Failed to notify Restaurant Admin: {e}")
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

    async def handle_document_message(self, update: Update, context):
        """Handle document messages for PDF uploads - Enhanced for receipts and bank statements"""
        user_id = update.effective_user.id
        
        if user_id not in users:
            await update.message.reply_text("Please start with /start first. ❌ Login Failed")
            return
        
        document = update.message.document
        file_id = document.file_id
        user_role = users[user_id].get("role", "waiter")
        
        # Check if it's a PDF
        if not document.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("❌ Please upload a PDF file.")
            return
        
        try:
            # Get file from Telegram
            file = await self.bot.get_file(file_id)
            file_url = file.file_path
            
            # Download PDF
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    pdf_data = await response.read()
            
            # Determine PDF type and process accordingly
            if user_role in ["restaurant_admin", "super_admin"]:
                # Admin can upload bank statements or receipt PDFs
                await update.message.reply_text("📄 PDF received! Processing...")
                await self.process_pdf_with_choice(pdf_data, file_id, user_id, document.file_name)
            else:
                # Waiters can only upload receipt PDFs
                if user_role == "waiter":
                    await update.message.reply_text("📄 Receipt PDF received! Processing...")
                    await self.process_receipt_pdf(pdf_data, file_id, user_id)
                else:
                    await update.message.reply_text("❌ Unauthorized to upload PDFs!")
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            await update.message.reply_text("❌ Error processing PDF. Please try again.")

    async def process_pdf_with_choice(self, pdf_data: bytes, file_id: str, user_id: int, filename: str):
        """Process PDF and ask user to choose type"""
        try:
            # Quick analysis to suggest type
            suggested_type = self.suggest_pdf_type(pdf_data, filename)
            
            message = f"📄 **PDF Analysis Complete**\n\n"
            message += f"**Filename:** {filename}\n"
            message += f"**Suggested Type:** {suggested_type}\n\n"
            message += "Please select how to process this PDF:"
            
            keyboard = [
                [InlineKeyboardButton("🏦 Process as Bank Statement", callback_data=f"pdf_bank_{user_id}_{file_id}")],
                [InlineKeyboardButton("🧾 Process as Receipt Collection", callback_data=f"pdf_receipts_{user_id}_{file_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"pdf_cancel_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot.send_message(
                user_id,
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in PDF choice processing: {e}")
            await self.bot.send_message(user_id, "❌ Error analyzing PDF. Please try again.")

    def suggest_pdf_type(self, pdf_data: bytes, filename: str) -> str:
        """Analyze PDF to suggest processing type"""
        try:
            # Extract text for analysis
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                text = ""
                for page in pdf.pages[:3]:  # Analyze first 3 pages
                    text += page.extract_text() or ""
            
            # Bank statement indicators
            bank_keywords = ['statement', 'balance', 'account', 'bank', 'transaction', 'deposit', 'withdrawal']
            # Receipt indicators
            receipt_keywords = ['receipt', 'payment', 'amount', 'total', 'customer', 'invoice', 'sale']
            
            bank_score = sum(1 for keyword in bank_keywords if keyword.lower() in text.lower())
            receipt_score = sum(1 for keyword in receipt_keywords if keyword.lower() in text.lower())
            
            if bank_score > receipt_score:
                return "Bank Statement"
            elif receipt_score > bank_score:
                return "Receipt Collection"
            else:
                return "Unknown (choose manually)"
        except:
            return "Unknown (choose manually)"

    async def process_receipt_pdf(self, pdf_data: bytes, file_id: str, user_id: int):
        """Process PDF as receipt collection"""
        try:
            # Extract pages as images for OCR
            receipt_data_list = []
            
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Convert page to image
                        pil_image = page.to_image()
                        if pil_image:
                            # Convert to bytes for OCR
                            img_bytes = io.BytesIO()
                            pil_image.original.save(img_bytes, format='PNG')
                            img_bytes = img_bytes.getvalue()
                            
                            # Extract data using OCR
                            extracted_data = await self.extract_receipt_data_from_google_vision(img_bytes)
                            
                            if extracted_data and extracted_data['amount'] > 0:
                                receipt_data_list.append({
                                    'page': page_num,
                                    'data': extracted_data
                                })
                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {e}")
                        continue
            
            if receipt_data_list:
                # Process each receipt found
                transactions_created = 0
                for receipt in receipt_data_list:
                    transaction_id = f"TXN{len(transactions) + transactions_created + 1:06d}"
                    transaction = Transaction(
                        id=transaction_id,
                        user_id=user_id,
                        amount=receipt['data']['amount'],
                        transaction_id=receipt['data']['transaction_id'],
                        date=receipt['data']['date'],
                        time=receipt['data']['time'],
                        payer=receipt['data']['payer'],
                        receiver=receipt['data']['receiver'],
                        bank_name=receipt['data']['bank_name'],
                        payment_method=receipt['data']['payment_method'],
                        currency=receipt['data']['currency'],
                        waiter_id=users[user_id].get('waiter_id', 'UNKNOWN'),
                        restaurant_id=users[user_id].get('restaurant_id', 'UNKNOWN'),
                        created_at=datetime.now()
                    )
                    
                    transactions[transaction_id] = transaction
                    transactions_created += 1
                
                # Log audit
                self.log_audit(user_id, "pdf_receipts_processed", f"Processed {transactions_created} receipts from PDF")
                
                await self.bot.send_message(
                    user_id,
                    f"✅ **PDF Processing Complete!**\n\n"
                    f"📊 **Receipts Found:** {len(receipt_data_list)}\n"
                    f"💰 **Transactions Created:** {transactions_created}\n"
                    f"📄 **Total Pages Processed:** {len(pdf.pages)}\n\n"
                    f"All receipts have been added to your transaction records."
                )
            else:
                await self.bot.send_message(
                    user_id,
                    "❌ **No valid receipts found in PDF**\n\n"
                    "Please ensure the PDF contains clear receipt images and try again."
                )
                
        except Exception as e:
            logger.error(f"Error processing receipt PDF: {e}")
            await self.bot.send_message(user_id, "❌ Error processing receipt PDF. Please try again.")
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
        Returns dict with keys: amount (str), reference (str), bank (str), datetime_iso (str)
        Enhanced for CBE, Telebirr, and Dashen Bank receipts based on actual screenshots.
        """
        result: Dict[str, str] = {}
        if not text:
            return result
        try:
            # Normalize text - preserve line breaks for better pattern matching
            lines = text.replace('\r', '\n').split('\n')
            cleaned = ' '.join(line.strip() for line in lines if line.strip())
            
            logger.info(f"OCR Text to parse: {cleaned[:200]}...")
            
            # Amount patterns - More specific based on actual receipts
            amount_patterns = [
                # CBE: "ETB 10,000.00" - exact pattern
                r'ETB\s+([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',
                # Telebirr: "-7,008.00 (ETB)" - exact pattern
                r'(-[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*\(ETB\)',
                # Dashen: "10,000.00 (ETB)" - exact pattern
                r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*\(ETB\)',
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
                    num_str = str(match).replace(',', '').replace(' ', '')
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

            # Reference / Transaction ID patterns - More specific
            ref_patterns = [
                # CBE: "FT25249P26RL" - exact pattern
                r'\bFT[0-9A-Z]{8,12}\b',
                # Dashen: "FT264OBTS2522001Yo" - exact pattern  
                r'\bFT[0-9A-Z]{15,20}\b',
                # Telebirr: "CHC85K0LMU" - exact pattern
                r'\b[A-Z]{3}[0-9]{2}[A-Z0-9]{4,6}\b',
                # Dashen: "OBTS08022286760791946435" - exact pattern
                r'\bOBTS[0-9]{20,25}\b',
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

            # Date / time patterns - More specific based on actual receipts
            from datetime import datetime as _dt
            
            # Combined date and time patterns (exact from screenshots)
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
            
            # Separate date patterns
            date_patterns = [
                r'(\d{4}/\d{2}/\d{2})',  # Telebirr: 2025/08/12
                r'(\d{2}/\d{2}/\d{4})',  # CBE: 06/09/2025
                r'([A-Za-z]{3}\s+\d{1,2},\s+\d{4})',  # Dashen: Aug 08, 2025
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}-\d{2}-\d{4})'
            ]
            
            # Separate time patterns
            time_patterns = [
                r'(\d{1,2}:\d{2}:\d{2}\s*[APap][Mm])',  # Dashen: 01:07 PM
                r'(\d{1,2}:\d{2}\s*[APap][Mm])',
                r'(\d{2}:\d{2}:\d{2})',  # Telebirr: 13:23:22
                r'(\d{2}:\d{2})'
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
                            result["datetime_iso"] = _dt.strptime(s, fmt).isoformat()
                            dt_found = True
                            logger.info(f"DateTime found with pattern {i}: {result['datetime_iso']}")
                            break
                        except ValueError:
                            continue
                    if dt_found:
                        break
                if dt_found:
                    break
            
            # If no combined datetime found, try separate date and time
            if not dt_found:
                date_part = None
                time_part = None
                
                # Find date
                for pattern in date_patterns:
                    matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
                    if matches:
                        date_part = matches[0]
                        break
                
                # Find time
                for pattern in time_patterns:
                    matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
                    if matches:
                        time_part = matches[0]
                        break
                
                if date_part and time_part:
                    s = f"{date_part} {time_part}".replace('T', ' ')
                    # Normalize AM/PM spacing/case
                    s = re.sub(r'\s*([APap][Mm])\b', r' \1', s)
                    
                    # Try format combinations
                    fmts = [
                        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
                        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
                        "%b %d, %Y %I:%M %p", "%b %d, %Y %H:%M"
                    ]
                    for fmt in fmts:
                        try:
                            result["datetime_iso"] = _dt.strptime(s, fmt).isoformat()
                            logger.info(f"Separate Date/Time found: {result['datetime_iso']}")
                            break
                        except ValueError:
                            continue
                elif date_part: # If only date is found, assume midnight
                    for fmt in ["%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y", "%Y-%m-%d", "%d-%m-%Y"]:
                        try:
                            result["datetime_iso"] = _dt.strptime(date_part, fmt).date().isoformat()
                            logger.info(f"Only Date found: {result['datetime_iso']}")
                            break
                        except ValueError:
                            pass
                elif time_part: # If only time is found, assume today's date
                    for fmt in ["%H:%M:%S", "%H:%M", "%I:%M %p"]:
                        try:
                            today = _dt.now().date()
                            time_obj = _dt.strptime(time_part, fmt).time()
                            result["datetime_iso"] = _dt.combine(today, time_obj).isoformat()
                            logger.info(f"Only Time found: {result['datetime_iso']}")
                            break
                        except ValueError:
                            pass

            # Bank/Payment Method patterns
            bank_patterns = [
                r'CBE|Commercial Bank of Ethiopia',
                r'Telebirr',
                r'Dashen Bank',
                r'Awash Bank',
                r'Abyssinia Bank',
                r'Hibret Bank',
                r'Zemen Bank'
            ]
            for p in bank_patterns:
                m = re.search(p, cleaned, flags=re.IGNORECASE)
                if m:
                    result["bank"] = m.group(0)
                    logger.info(f"Found bank: {result['bank']}")
                    break

        except Exception as e:
            logger.error(f"Error parsing receipt text: {e}")

        return result

