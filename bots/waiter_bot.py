"""
Waiter Bot for VeriPay - Handles payment screenshot uploads and verification
"""
import asyncio
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yaml
from loguru import logger
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import DatabaseManager, WaiterOperations, TransactionOperations
from core.ocr_extractor import OCRExtractor
from core.fraud_detector import FraudDetector
from core.bank_verifier import BankVerifier
from database.models import VerificationStatus, BankType


class WaiterStates(StatesGroup):
    """States for waiter bot conversation flow"""
    waiting_for_screenshot = State()
    confirming_details = State()
    waiting_for_waiter_info = State()


class WaiterBot:
    """Telegram bot for waiters to upload payment screenshots"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize waiter bot"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Initialize bot
        self.bot = Bot(token=self.config['telegram']['waiter_bot_token'])
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        
        # Initialize components
        self.db_manager = DatabaseManager(config_path)
        self.ocr_extractor = OCRExtractor(config_path)
        self.fraud_detector = FraudDetector(config_path)
        self.bank_verifier = BankVerifier(config_path)
        
        # Setup handlers
        self._setup_handlers()
        
        # Create uploads directory
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)
    
    def _setup_handlers(self):
        """Setup bot command and message handlers"""
        # Start command
        self.router.message(Command("start"))(self.cmd_start)
        
        # Help command
        self.router.message(Command("help"))(self.cmd_help)
        
        # Upload screenshot command
        self.router.message(Command("upload"))(self.cmd_upload)
        
        # Handle photo messages
        self.router.message(lambda message: message.photo)(self.handle_photo)
        
        # Handle callback queries
        self.router.callback_query()(self.handle_callback)
        
        # Handle text messages
        self.router.message()(self.handle_text)
        
        # Add router to dispatcher
        self.dp.include_router(self.router)
    
    async def cmd_start(self, message: types.Message):
        """Handle /start command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is registered waiter
            session = self.db_manager.get_session()
            waiter = WaiterOperations.get_waiter_by_telegram_id(session, user_id)
            
            if waiter:
                welcome_text = f"""
🎉 Welcome back, {waiter.name}!

I'm VeriPay, your payment verification assistant. I help you verify payment screenshots quickly and securely.

📱 **How to use:**
• Send me a payment screenshot
• I'll extract and verify the transaction details
• You'll get instant verification results

🔧 **Commands:**
/upload - Upload a payment screenshot
/help - Show this help message

Ready to verify a payment? Just send me a screenshot! 📸
                """
            else:
                welcome_text = """
🎉 Welcome to VeriPay!

I'm your payment verification assistant. I help you verify payment screenshots quickly and securely.

📱 **How to use:**
• Send me a payment screenshot
• I'll extract and verify the transaction details
• You'll get instant verification results

🔧 **Commands:**
/upload - Upload a payment screenshot
/help - Show this help message

⚠️ **Note:** You need to be registered as a waiter to use this service. Please contact your manager.

Ready to verify a payment? Just send me a screenshot! 📸
                """
            
            await message.answer(welcome_text)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.answer("Sorry, something went wrong. Please try again.")
        finally:
            session.close()
    
    async def cmd_help(self, message: types.Message):
        """Handle /help command"""
        help_text = """
📚 **VeriPay Help**

🔍 **What I do:**
• Extract transaction details from payment screenshots
• Detect potential fraud and manipulation
• Verify transactions with bank APIs
• Provide instant verification results

📱 **How to use:**
1. Send me a payment screenshot (photo)
2. I'll analyze the image and extract details
3. Review the extracted information
4. Confirm to proceed with verification
5. Get instant verification results

🔧 **Commands:**
/start - Start the bot
/upload - Upload a payment screenshot
/help - Show this help message

💡 **Tips:**
• Make sure the screenshot is clear and readable
• Include the full transaction details
• Ensure good lighting for better OCR results

❓ **Need help?** Contact your manager or admin.
        """
        await message.answer(help_text)
    
    async def cmd_upload(self, message: types.Message, state: FSMContext):
        """Handle /upload command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is registered waiter
            session = self.db_manager.get_session()
            waiter = WaiterOperations.get_waiter_by_telegram_id(session, user_id)
            
            if not waiter:
                await message.answer("⚠️ You need to be registered as a waiter to use this service. Please contact your manager.")
                return
            
            await state.set_state(WaiterStates.waiting_for_screenshot)
            await message.answer(
                "📸 Please send me the payment screenshot.\n\n"
                "Make sure the image is clear and shows all transaction details including:\n"
                "• Transaction reference/STN number\n"
                "• Amount\n"
                "• Date and time\n"
                "• Sender and receiver information"
            )
            
        except Exception as e:
            logger.error(f"Error in upload command: {e}")
            await message.answer("Sorry, something went wrong. Please try again.")
        finally:
            session.close()
    
    async def handle_photo(self, message: types.Message, state: FSMContext):
        """Handle photo messages (screenshots)"""
        try:
            current_state = await state.get_state()
            
            if current_state != WaiterStates.waiting_for_screenshot:
                await message.answer("Please use /upload command to start the verification process.")
                return
            
            user_id = str(message.from_user.id)
            
            # Check if user is registered waiter
            session = self.db_manager.get_session()
            waiter = WaiterOperations.get_waiter_by_telegram_id(session, user_id)
            
            if not waiter:
                await message.answer("⚠️ You need to be registered as a waiter to use this service.")
                return
            
            # Download the photo
            photo = message.photo[-1]  # Get the largest photo
            file_info = await self.bot.get_file(photo.file_id)
            
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"waiter_{user_id}_{timestamp}.jpg"
            filepath = self.uploads_dir / filename
            
            # Download file
            await self.bot.download_file(file_info.file_path, str(filepath))
            
            await message.answer("🔍 Analyzing screenshot... Please wait.")
            
            # Process the screenshot
            result = await self._process_screenshot(filepath, waiter, session)
            
            if result['success']:
                # Store extracted data in state
                await state.update_data(
                    extracted_data=result['extracted_data'],
                    screenshot_path=str(filepath),
                    waiter_id=waiter.id,
                    restaurant_id=waiter.restaurant_id
                )
                
                # Show extracted data for confirmation
                await self._show_extracted_data(message, result['extracted_data'])
                await state.set_state(WaiterStates.confirming_details)
            else:
                await message.answer(f"❌ Error processing screenshot: {result['error']}")
                await state.clear()
            
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await message.answer("Sorry, something went wrong while processing the screenshot. Please try again.")
            await state.clear()
        finally:
            session.close()
    
    async def _process_screenshot(self, filepath: Path, waiter, session) -> Dict:
        """Process uploaded screenshot"""
        try:
            # 1. Extract data using OCR
            ocr_result = self.ocr_extractor.extract_transaction_data(str(filepath))
            
            if 'error' in ocr_result:
                return {
                    'success': False,
                    'error': ocr_result['error']
                }
            
            # 2. Detect fraud
            fraud_result = self.fraud_detector.analyze_screenshot(str(filepath))
            
            # 3. Validate extracted data
            is_valid, issues = self.ocr_extractor.validate_extraction(ocr_result)
            
            if not is_valid:
                return {
                    'success': False,
                    'error': f"Data validation failed: {'; '.join(issues)}"
                }
            
            # 4. Check for duplicate screenshot
            if ocr_result.get('screenshot_hash'):
                duplicate = TransactionOperations.check_duplicate_screenshot(
                    session, ocr_result['screenshot_hash']
                )
                if duplicate:
                    return {
                        'success': False,
                        'error': "This screenshot has already been processed"
                    }
            
            return {
                'success': True,
                'extracted_data': {
                    'ocr_result': ocr_result,
                    'fraud_result': fraud_result,
                    'validation_issues': issues
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing screenshot: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _show_extracted_data(self, message: types.Message, extracted_data: Dict):
        """Show extracted data for confirmation"""
        ocr_result = extracted_data['ocr_result']
        fraud_result = extracted_data['fraud_result']
        
        # Create confirmation message
        confirmation_text = f"""
📋 **Extracted Transaction Details:**

🔢 **STN Number:** {ocr_result.get('stn_number', 'Not found')}
💰 **Amount:** ETB {ocr_result.get('amount', 0):,.2f}
📅 **Date:** {ocr_result.get('transaction_date', 'Not found')}
👤 **Sender:** {ocr_result.get('sender_account', 'Not found')}
👥 **Receiver:** {ocr_result.get('receiver_account', 'Not found')}
🏦 **Bank:** {ocr_result.get('bank_type', 'Unknown').upper()}

🔍 **Fraud Analysis:**
• Suspicion Level: {fraud_result.get('suspicion_level', 'Unknown')}
• Fraud Score: {fraud_result.get('fraud_score', 0):.2%}
• Indicators: {', '.join(fraud_result.get('fraud_indicators', [])) or 'None'}

📊 **Confidence:** {ocr_result.get('confidence', 0):.2%}

Please confirm if these details are correct:
        """
        
        # Create confirmation keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm & Verify", callback_data="confirm_verify"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_verification")
            ]
        ])
        
        await message.answer(confirmation_text, reply_markup=keyboard)
    
    async def handle_callback(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle callback queries"""
        try:
            data = callback_query.data
            
            if data == "confirm_verify":
                await self._handle_verification_confirmation(callback_query, state)
            elif data == "cancel_verification":
                await self._handle_verification_cancellation(callback_query, state)
            else:
                await callback_query.answer("Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await callback_query.answer("Sorry, something went wrong.")
    
    async def _handle_verification_confirmation(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle verification confirmation"""
        try:
            await callback_query.answer("Processing verification...")
            
            # Get stored data
            data = await state.get_data()
            extracted_data = data['extracted_data']
            screenshot_path = data['screenshot_path']
            waiter_id = data['waiter_id']
            restaurant_id = data['restaurant_id']
            
            # Create transaction in database
            session = self.db_manager.get_session()
            
            ocr_result = extracted_data['ocr_result']
            fraud_result = extracted_data['fraud_result']
            
            # Determine verification status based on fraud analysis
            if fraud_result['is_suspicious']:
                verification_status = VerificationStatus.SUSPICIOUS
            else:
                verification_status = VerificationStatus.PENDING
            
            # Create transaction
            transaction = TransactionOperations.create_transaction(
                session=session,
                stn_number=ocr_result['stn_number'],
                amount=ocr_result['amount'],
                waiter_id=waiter_id,
                restaurant_id=restaurant_id,
                bank_type=BankType(ocr_result['bank_type']),
                sender_account=ocr_result.get('sender_account'),
                receiver_account=ocr_result.get('receiver_account'),
                transaction_date=ocr_result.get('transaction_date'),
                screenshot_path=screenshot_path
            )
            
            # Update with OCR and fraud data
            TransactionOperations.update_ocr_data(
                session, transaction.id, ocr_result, ocr_result.get('confidence', 0)
            )
            
            TransactionOperations.update_fraud_detection(
                session, transaction.id, fraud_result['fraud_score'], 
                fraud_result['fraud_indicators']
            )
            
            # Update verification status
            TransactionOperations.update_transaction_status(
                session, transaction.id, verification_status, 
                fraud_result['fraud_score'], 
                f"Fraud level: {fraud_result['suspicion_level']}"
            )
            
            # Perform bank verification
            bank_verification = self.bank_verifier.verify_transaction(
                stn_number=ocr_result['stn_number'],
                amount=ocr_result['amount'],
                bank_type=ocr_result['bank_type'],
                transaction_date=ocr_result.get('transaction_date')
            )
            
            # Update bank verification results
            TransactionOperations.update_bank_verification(
                session, transaction.id, bank_verification['verified'], 
                bank_verification
            )
            
            # Determine final status
            final_status = verification_status
            if bank_verification['verified']:
                final_status = VerificationStatus.VERIFIED
            elif verification_status == VerificationStatus.SUSPICIOUS:
                final_status = VerificationStatus.SUSPICIOUS
            else:
                final_status = VerificationStatus.FAILED
            
            # Update final status
            TransactionOperations.update_transaction_status(
                session, transaction.id, final_status,
                max(ocr_result.get('confidence', 0), fraud_result['fraud_score']),
                f"Bank verified: {bank_verification['verified']}"
            )
            
            # Send result to waiter
            await self._send_verification_result(callback_query.message, final_status, 
                                               ocr_result, fraud_result, bank_verification)
            
            # Notify admin (if configured)
            await self._notify_admin(transaction, final_status, ocr_result, fraud_result)
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error in verification confirmation: {e}")
            await callback_query.message.answer("Sorry, something went wrong during verification.")
            await state.clear()
        finally:
            session.close()
    
    async def _handle_verification_cancellation(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle verification cancellation"""
        await callback_query.answer("Verification cancelled")
        await callback_query.message.edit_text("❌ Verification cancelled. You can upload a new screenshot anytime.")
        await state.clear()
    
    async def _send_verification_result(self, message: types.Message, status: VerificationStatus,
                                      ocr_result: Dict, fraud_result: Dict, bank_verification: Dict):
        """Send verification result to waiter"""
        # Create status emoji and message
        if status == VerificationStatus.VERIFIED:
            status_emoji = "✅"
            status_text = "VERIFIED"
            result_message = "Payment verification successful!"
        elif status == VerificationStatus.SUSPICIOUS:
            status_emoji = "⚠️"
            status_text = "SUSPICIOUS"
            result_message = "Payment requires manual review."
        elif status == VerificationStatus.FAILED:
            status_emoji = "❌"
            status_text = "FAILED"
            result_message = "Payment verification failed."
        else:
            status_emoji = "⏳"
            status_text = "PENDING"
            result_message = "Payment verification pending."
        
        result_text = f"""
{status_emoji} **Verification Result: {status_text}**

{result_message}

📋 **Transaction Details:**
• STN: {ocr_result.get('stn_number', 'N/A')}
• Amount: ETB {ocr_result.get('amount', 0):,.2f}
• Bank: {ocr_result.get('bank_type', 'Unknown').upper()}

🔍 **Analysis Results:**
• OCR Confidence: {ocr_result.get('confidence', 0):.2%}
• Fraud Score: {fraud_result.get('fraud_score', 0):.2%}
• Bank Verification: {'✅ Yes' if bank_verification['verified'] else '❌ No'}

💡 **Next Steps:**
{'✅ Transaction verified - you can proceed' if status == VerificationStatus.VERIFIED else '⚠️ Please contact your manager for manual review' if status == VerificationStatus.SUSPICIOUS else '❌ Please request a new payment from the customer'}
        """
        
        await message.edit_text(result_text)
    
    async def _notify_admin(self, transaction, status: VerificationStatus, 
                          ocr_result: Dict, fraud_result: Dict):
        """Notify admin about new verification"""
        try:
            # Get admin chat IDs from config
            admin_chat_ids = self.config['telegram'].get('admin_user_ids', [])
            
            if not admin_chat_ids:
                return
            
            notification_text = f"""
🔔 **New Payment Verification**

📋 **Transaction Details:**
• STN: {ocr_result.get('stn_number', 'N/A')}
• Amount: ETB {ocr_result.get('amount', 0):,.2f}
• Bank: {ocr_result.get('bank_type', 'Unknown').upper()}
• Waiter ID: {transaction.waiter_id}

🔍 **Verification Status:** {status.value.upper()}
• Fraud Score: {fraud_result.get('fraud_score', 0):.2%}
• OCR Confidence: {ocr_result.get('confidence', 0):.2%}

⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            for chat_id in admin_chat_ids:
                try:
                    await self.bot.send_message(chat_id, notification_text)
                except Exception as e:
                    logger.error(f"Failed to notify admin {chat_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    async def handle_text(self, message: types.Message, state: FSMContext):
        """Handle text messages"""
        current_state = await state.get_state()
        
        if current_state == WaiterStates.waiting_for_screenshot:
            await message.answer("Please send me a payment screenshot (photo), not text.")
        else:
            await message.answer("Use /upload to start verification or /help for assistance.")
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Waiter Bot...")
        await self.dp.start_polling(self.bot)


if __name__ == "__main__":
    # Setup logging
    logger.add("logs/waiter_bot.log", rotation="1 day", retention="7 days")
    
    # Create and run bot
    bot = WaiterBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        traceback.print_exc() 