#!/usr/bin/env python3
import re

# Read the file
with open('veripay_bot_complete.py', 'r') as f:
    content = f.read()

# Find the run method and replace it
pattern = r'    async def run\(self\):.*?(?=if __name__)'
replacement = '''    async def run(self):
        """Run the bot"""
        if self.running:
            logger.warning("Bot is already running!")
            return
        
        try:
            self.running = True
            logger.info("Starting VeriPay Bot - COMPLETE VERSION...")
            logger.info("Send a message to @Verifpay_bot now!")
            
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Clear webhook
            await self.bot.delete_webhook()
            
            logger.info("Bot is running! Press Ctrl+C to stop.")
            
            # Start polling for updates
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.running = False
            if self.application:
                await self.application.stop()

'''

# Replace the method
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('veripay_bot_complete.py', 'w') as f:
    f.write(new_content)

print("Fixed run method")
