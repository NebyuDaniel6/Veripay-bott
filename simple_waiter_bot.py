#!/usr/bin/env python3
"""
Simple VeriPay Waiter Bot - For testing with minimal dependencies
"""
import asyncio
import yaml
import json
from datetime import datetime
from pathlib import Path

# Try to import aiogram, but don't fail if not available
try:
    from aiogram import Bot, Dispatcher, types, Router
    from aiogram.filters import Command
    from aiogram.fsm.storage.memory import MemoryStorage
    AIOGRAM_AVAILABLE = True
except ImportError:
    AIOGRAM_AVAILABLE = False
    print("⚠️  aiogram not installed. Install with: pip3 install aiogram")


class SimpleWaiterBot:
    """Simplified waiter bot for testing"""
    
    def __init__(self):
        """Initialize the bot"""
        # Load config
        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.bot_token = self.config['telegram']['waiter_bot_token']
        self.bot = None
        self.dp = None
        
        # Create uploads directory
        Path('uploads').mkdir(exist_ok=True)
        Path('logs').mkdir(exist_ok=True)
    
    async def start(self):
        """Start the bot"""
        if not AIOGRAM_AVAILABLE:
            print("❌ aiogram not available. Please install it first:")
            print("pip3 install aiogram")
            return
        
        try:
            # Initialize bot
            self.bot = Bot(token=self.bot_token)
            self.dp = Dispatcher(storage=MemoryStorage())
            
            # Setup handlers
            self._setup_handlers()
            
            print(f"🤖 Starting VeriPay Waiter Bot...")
            print(f"📱 Bot: @Verifpay_bot")
            print(f"🔗 Link: https://t.me/Verifpay_bot")
            print(f"⏹️  Press Ctrl+C to stop")
            
            # Start polling
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
    
    def _setup_handlers(self):
        """Setup bot handlers"""
        router = Router()
        
        @router.message(Command("start"))
        async def cmd_start(message: types.Message):
            """Handle /start command"""
            welcome_text = f"""
🎉 Welcome to VeriPay!

I'm your payment verification assistant. I help you verify payment screenshots quickly and securely.

📱 **How to use:**
• Send me a payment screenshot
• I'll extract and verify the transaction details
• You'll get instant verification results

🔧 **Commands:**
/upload - Upload a payment screenshot
/help - Show this help message

Ready to verify a payment? Just send me a screenshot! 📸

**Test Mode:** This is a simplified version for testing.
            """
            await message.answer(welcome_text)
        
        @router.message(Command("help"))
        async def cmd_help(message: types.Message):
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

💡 **Tips:**
• Make sure the screenshot is clear and readable
• Include the full transaction details
• Ensure good lighting for better OCR results

❓ **Need help?** Contact your manager or admin.

**Test Mode:** This is a simplified version for testing.
            """
            await message.answer(help_text)
        
        @router.message(Command("upload"))
        async def cmd_upload(message: types.Message):
            """Handle /upload command"""
            await message.answer(
                "📸 Please send me the payment screenshot.\n\n"
                "Make sure the image is clear and shows all transaction details including:\n"
                "• Transaction reference/STN number\n"
                "• Amount\n"
                "• Date and time\n"
                "• Sender and receiver information\n\n"
                "**Test Mode:** I'll simulate the verification process."
            )
        
        @router.message(lambda message: message.photo)
        async def handle_photo(message: types.Message):
            """Handle photo messages (screenshots)"""
            try:
                await message.answer("🔍 Analyzing screenshot... Please wait.")
                
                # Simulate processing delay
                await asyncio.sleep(2)
                
                # Simulate extracted data
                simulated_data = {
                    'stn_number': 'STN12345678',
                    'amount': 1500.00,
                    'transaction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'sender_account': 'John Doe',
                    'receiver_account': 'Sample Restaurant',
                    'bank_type': 'cbe',
                    'confidence': 0.85
                }
                
                # Create result message
                result_text = f"""
📋 **Extracted Transaction Details:**

🔢 **STN Number:** {simulated_data['stn_number']}
💰 **Amount:** ETB {simulated_data['amount']:,.2f}
📅 **Date:** {simulated_data['transaction_date']}
👤 **Sender:** {simulated_data['sender_account']}
👥 **Receiver:** {simulated_data['receiver_account']}
🏦 **Bank:** {simulated_data['bank_type'].upper()}

🔍 **Fraud Analysis:**
• Suspicion Level: LOW
• Fraud Score: 0.15 (15%)
• Indicators: None detected

📊 **Confidence:** {simulated_data['confidence']:.2%}

✅ **Verification Result: VERIFIED**

💡 **Next Steps:**
✅ Transaction verified - you can proceed

**Test Mode:** This is simulated data for testing purposes.
                """
                
                await message.answer(result_text)
                
            except Exception as e:
                await message.answer(f"❌ Error processing screenshot: {str(e)}")
        
        @router.message()
        async def handle_text(message: types.Message):
            """Handle text messages"""
            await message.answer(
                "Use /upload to start verification or /help for assistance.\n\n"
                "**Test Mode:** This is a simplified version for testing."
            )
        
        # Add router to dispatcher
        self.dp.include_router(router)


async def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                VeriPay Simple Waiter Bot                     ║
║                                                              ║
║  🤖 Testing version with minimal dependencies               ║
║  📱 Ready to receive payment screenshots                    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create and run bot
    bot = SimpleWaiterBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 