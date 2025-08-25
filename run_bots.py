#!/usr/bin/env python3
"""
VeriPay Bot Runner - Run both waiter and admin bots
"""
import asyncio
import sys
import os
import signal
from pathlib import Path
from loguru import logger

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bots.waiter_bot import WaiterBot
from bots.admin_bot import AdminBot


class BotRunner:
    """Runner for both VeriPay bots"""
    
    def __init__(self):
        """Initialize bot runner"""
        self.waiter_bot = None
        self.admin_bot = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def start_bots(self):
        """Start both bots"""
        try:
            logger.info("Starting VeriPay bots...")
            
            # Initialize bots
            self.waiter_bot = WaiterBot()
            self.admin_bot = AdminBot()
            
            # Start both bots concurrently
            self.running = True
            
            # Create tasks for both bots
            waiter_task = asyncio.create_task(self._run_waiter_bot())
            admin_task = asyncio.create_task(self._run_admin_bot())
            
            logger.info("✅ Both bots started successfully!")
            logger.info("🤖 Waiter Bot: Ready to receive payment screenshots")
            logger.info("👨‍💼 Admin Bot: Ready for management tasks")
            logger.info("Press Ctrl+C to stop both bots")
            
            # Wait for both tasks
            await asyncio.gather(waiter_task, admin_task)
            
        except Exception as e:
            logger.error(f"Error starting bots: {e}")
            raise
    
    async def _run_waiter_bot(self):
        """Run waiter bot"""
        try:
            await self.waiter_bot.start()
        except Exception as e:
            logger.error(f"Waiter bot error: {e}")
            self.running = False
    
    async def _run_admin_bot(self):
        """Run admin bot"""
        try:
            await self.admin_bot.start()
        except Exception as e:
            logger.error(f"Admin bot error: {e}")
            self.running = False
    
    async def stop_bots(self):
        """Stop both bots"""
        logger.info("Stopping VeriPay bots...")
        self.running = False
        
        if self.waiter_bot:
            try:
                await self.waiter_bot.bot.session.close()
            except:
                pass
        
        if self.admin_bot:
            try:
                await self.admin_bot.bot.session.close()
            except:
                pass
        
        logger.info("✅ Both bots stopped")


def main():
    """Main function"""
    # Setup logging
    logger.add("logs/bot_runner.log", rotation="1 day", retention="7 days")
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Print banner
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    VeriPay Bot Runner                       ║
║                                                              ║
║  🤖 Waiter Bot + 👨‍💼 Admin Bot                           ║
║                                                              ║
║  Starting both Telegram bots for payment verification...    ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Create and run bot runner
    runner = BotRunner()
    
    try:
        asyncio.run(runner.start_bots())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        asyncio.run(runner.stop_bots())
        logger.info("Bot runner shutdown complete")


if __name__ == "__main__":
    main() 