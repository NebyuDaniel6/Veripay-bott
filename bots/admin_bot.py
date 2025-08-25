"""
Admin Bot for VeriPay - Manages verifications, reports, and statement uploads
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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import (
    DatabaseManager, AdminOperations, TransactionOperations, 
    AuditOperations, RestaurantOperations, WaiterOperations
)
from core.audit_engine import AuditEngine
from database.models import VerificationStatus, BankType, Transaction, Restaurant, Waiter


class AdminStates(StatesGroup):
    """States for admin bot conversation flow"""
    waiting_for_statement = State()
    waiting_for_restaurant_info = State()
    waiting_for_waiter_info = State()


class AdminBot:
    """Telegram bot for admins to manage verifications and reports"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize admin bot"""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Initialize bot
        self.bot = Bot(token=self.config['telegram']['admin_bot_token'])
        self.dp = Dispatcher(storage=MemoryStorage())
        self.router = Router()
        
        # Initialize components
        self.db_manager = DatabaseManager(config_path)
        self.audit_engine = AuditEngine(config_path)
        
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
        
        # Dashboard command
        self.router.message(Command("dashboard"))(self.cmd_dashboard)
        
        # Transactions command
        self.router.message(Command("transactions"))(self.cmd_transactions)
        
        # Statement command
        self.router.message(Command("statement"))(self.cmd_statement)
        
        # Report command
        self.router.message(Command("report"))(self.cmd_report)
        
        # Waiters command
        self.router.message(Command("waiters"))(self.cmd_waiters)
        
        # Handle photo messages (statements)
        self.router.message(lambda message: message.photo)(self.handle_photo)
        
        # Handle document messages (statements)
        self.router.message(lambda message: message.document)(self.handle_document)
        
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
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if admin:
                welcome_text = f"""
🎉 Welcome back, {admin.name}!

I'm VeriPay Admin, your payment verification management system.

📊 **Quick Stats:**
• Monitor payment verifications
• Generate audit reports
• Manage waiters and restaurants
• Reconcile bank statements

🔧 **Commands:**
/dashboard - View system overview
/transactions - View recent transactions
/statement - Upload bank statement
/report - Generate audit report
/waiters - Manage waiters
/help - Show help

Ready to manage your payment verifications! 💼
                """
            else:
                welcome_text = """
🎉 Welcome to VeriPay Admin!

I'm your payment verification management system.

⚠️ **Access Required:**
You need admin privileges to use this bot. Please contact the system administrator.

🔧 **Available Commands:**
/help - Show help message

For access, please provide your admin credentials to the system administrator.
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
📚 **VeriPay Admin Help**

🔍 **What I do:**
• Monitor payment verifications in real-time
• Generate comprehensive audit reports
• Reconcile transactions with bank statements
• Manage waiters and restaurant settings
• View system analytics and statistics

📊 **Dashboard Features:**
• Real-time verification status
• Fraud detection alerts
• Transaction volume statistics
• System performance metrics

📋 **Transaction Management:**
• View all payment verifications
• Filter by status, date, waiter
• Override verification results
• Export transaction data

📄 **Statement Reconciliation:**
• Upload bank statements (Excel, CSV, PDF)
• Automatic transaction matching
• Discrepancy identification
• Audit trail generation

📈 **Reporting:**
• Generate PDF/Excel audit reports
• Custom date range reports
• Fraud analysis reports
• Performance analytics

👥 **User Management:**
• Add/remove waiters
• Manage restaurant settings
• View user activity logs
• Access control management

🔧 **Commands:**
/start - Start the bot
/dashboard - View system overview
/transactions - View recent transactions
/statement - Upload bank statement
/report - Generate audit report
/waiters - Manage waiters
/help - Show this help message

❓ **Need help?** Contact the system administrator.
        """
        await message.answer(help_text)
    
    async def cmd_dashboard(self, message: types.Message):
        """Handle /dashboard command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to access the dashboard.")
                return
            
            # Get dashboard statistics
            stats = await self._get_dashboard_stats(session)
            
            dashboard_text = f"""
📊 **VeriPay Dashboard**

📈 **Today's Activity:**
• New Transactions: {stats['today_transactions']}
• Verified: {stats['today_verified']}
• Failed: {stats['today_failed']}
• Suspicious: {stats['today_suspicious']}

💰 **Financial Summary:**
• Total Amount Today: ETB {stats['today_amount']:,.2f}
• Verified Amount: ETB {stats['today_verified_amount']:,.2f}
• Pending Amount: ETB {stats['today_pending_amount']:,.2f}

👥 **User Activity:**
• Active Waiters: {stats['active_waiters']}
• Restaurants: {stats['total_restaurants']}

⚠️ **Alerts:**
• High Fraud Rate: {'Yes' if stats['high_fraud_rate'] else 'No'}
• Pending Verifications: {stats['pending_verifications']}
• System Issues: {'Yes' if stats['system_issues'] else 'No'}

🕒 **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Create dashboard keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📋 View Transactions", callback_data="view_transactions"),
                    InlineKeyboardButton(text="📊 Generate Report", callback_data="generate_report")
                ],
                [
                    InlineKeyboardButton(text="📄 Upload Statement", callback_data="upload_statement"),
                    InlineKeyboardButton(text="👥 Manage Users", callback_data="manage_users")
                ]
            ])
            
            await message.answer(dashboard_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in dashboard command: {e}")
            await message.answer("Sorry, something went wrong while loading the dashboard.")
        finally:
            session.close()
    
    async def _get_dashboard_stats(self, session) -> Dict:
        """Get dashboard statistics"""
        try:
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())
            
            # Get today's transactions
            today_transactions = session.query(Transaction).filter(
                Transaction.created_at >= today_start,
                Transaction.created_at <= today_end
            ).all()
            
            # Calculate statistics
            stats = {
                'today_transactions': len(today_transactions),
                'today_verified': len([t for t in today_transactions if t.verification_status == VerificationStatus.VERIFIED]),
                'today_failed': len([t for t in today_transactions if t.verification_status == VerificationStatus.FAILED]),
                'today_suspicious': len([t for t in today_transactions if t.verification_status == VerificationStatus.SUSPICIOUS]),
                'today_amount': sum(t.amount for t in today_transactions),
                'today_verified_amount': sum(t.amount for t in today_transactions if t.verification_status == VerificationStatus.VERIFIED),
                'today_pending_amount': sum(t.amount for t in today_transactions if t.verification_status == VerificationStatus.PENDING),
                'active_waiters': session.query(Waiter).filter(Waiter.is_active == True).count(),
                'total_restaurants': session.query(Restaurant).filter(Restaurant.is_active == True).count(),
                'pending_verifications': session.query(Transaction).filter(Transaction.verification_status == VerificationStatus.PENDING).count(),
                'high_fraud_rate': len([t for t in today_transactions if t.fraud_score and t.fraud_score > 0.7]) > len(today_transactions) * 0.1,
                'system_issues': False  # Placeholder for system health check
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                'today_transactions': 0,
                'today_verified': 0,
                'today_failed': 0,
                'today_suspicious': 0,
                'today_amount': 0,
                'today_verified_amount': 0,
                'today_pending_amount': 0,
                'active_waiters': 0,
                'total_restaurants': 0,
                'pending_verifications': 0,
                'high_fraud_rate': False,
                'system_issues': False
            }
    
    async def cmd_transactions(self, message: types.Message):
        """Handle /transactions command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to view transactions.")
                return
            
            # Get recent transactions
            recent_transactions = session.query(Transaction).order_by(
                Transaction.created_at.desc()
            ).limit(10).all()
            
            if not recent_transactions:
                await message.answer("No transactions found.")
                return
            
            transactions_text = "📋 **Recent Transactions:**\n\n"
            
            for i, transaction in enumerate(recent_transactions, 1):
                status_emoji = {
                    VerificationStatus.VERIFIED: "✅",
                    VerificationStatus.FAILED: "❌",
                    VerificationStatus.SUSPICIOUS: "⚠️",
                    VerificationStatus.PENDING: "⏳",
                    VerificationStatus.OVERRIDDEN: "🔄"
                }.get(transaction.verification_status, "❓")
                
                transactions_text += f"""
{i}. {status_emoji} **{transaction.stn_number}**
   💰 ETB {transaction.amount:,.2f}
   👤 Waiter: {transaction.waiter.name if transaction.waiter else 'Unknown'}
   🏦 {transaction.bank_type.value.upper()}
   📅 {transaction.created_at.strftime('%Y-%m-%d %H:%M')}
   🔍 {transaction.verification_status.value.title()}
                """
            
            # Create transactions keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔍 View All", callback_data="view_all_transactions"),
                    InlineKeyboardButton(text="📊 Filter", callback_data="filter_transactions")
                ],
                [
                    InlineKeyboardButton(text="📄 Export", callback_data="export_transactions"),
                    InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_transactions")
                ]
            ])
            
            await message.answer(transactions_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in transactions command: {e}")
            await message.answer("Sorry, something went wrong while loading transactions.")
        finally:
            session.close()
    
    async def cmd_statement(self, message: types.Message, state: FSMContext):
        """Handle /statement command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to upload statements.")
                return
            
            await state.set_state(AdminStates.waiting_for_statement)
            await message.answer(
                "📄 Please upload your bank statement file.\n\n"
                "Supported formats:\n"
                "• Excel (.xlsx, .xls)\n"
                "• CSV (.csv)\n"
                "• PDF (.pdf)\n\n"
                "The file should contain:\n"
                "• Transaction reference numbers\n"
                "• Amounts\n"
                "• Dates\n"
                "• Sender/receiver information"
            )
            
        except Exception as e:
            logger.error(f"Error in statement command: {e}")
            await message.answer("Sorry, something went wrong. Please try again.")
        finally:
            session.close()
    
    async def cmd_report(self, message: types.Message):
        """Handle /report command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to generate reports.")
                return
            
            # Create report options keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Today's Report", callback_data="report_today"),
                    InlineKeyboardButton(text="📅 This Week", callback_data="report_week")
                ],
                [
                    InlineKeyboardButton(text="📅 This Month", callback_data="report_month"),
                    InlineKeyboardButton(text="📅 Custom Range", callback_data="report_custom")
                ],
                [
                    InlineKeyboardButton(text="🔍 Fraud Report", callback_data="report_fraud"),
                    InlineKeyboardButton(text="📈 Performance Report", callback_data="report_performance")
                ]
            ])
            
            await message.answer(
                "📊 **Generate Audit Report**\n\n"
                "Select the type of report you want to generate:",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in report command: {e}")
            await message.answer("Sorry, something went wrong. Please try again.")
        finally:
            session.close()
    
    async def cmd_waiters(self, message: types.Message):
        """Handle /waiters command"""
        try:
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to manage waiters.")
                return
            
            # Get all waiters
            waiters = session.query(Waiter).filter(Waiter.is_active == True).all()
            
            if not waiters:
                await message.answer("No active waiters found.")
                return
            
            waiters_text = "👥 **Active Waiters:**\n\n"
            
            for i, waiter in enumerate(waiters, 1):
                restaurant_name = waiter.restaurant.name if waiter.restaurant else "Unassigned"
                waiters_text += f"""
{i}. **{waiter.name}**
   📱 ID: {waiter.telegram_id}
   🏪 Restaurant: {restaurant_name}
   📅 Joined: {waiter.created_at.strftime('%Y-%m-%d')}
                """
            
            # Create waiters keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ Add Waiter", callback_data="add_waiter"),
                    InlineKeyboardButton(text="✏️ Edit Waiter", callback_data="edit_waiter")
                ],
                [
                    InlineKeyboardButton(text="📊 Waiter Stats", callback_data="waiter_stats"),
                    InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_waiters")
                ]
            ])
            
            await message.answer(waiters_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error in waiters command: {e}")
            await message.answer("Sorry, something went wrong while loading waiters.")
        finally:
            session.close()
    
    async def handle_photo(self, message: types.Message, state: FSMContext):
        """Handle photo messages (statements)"""
        await self._handle_statement_file(message, state, "photo")
    
    async def handle_document(self, message: types.Message, state: FSMContext):
        """Handle document messages (statements)"""
        await self._handle_statement_file(message, state, "document")
    
    async def _handle_statement_file(self, message: types.Message, state: FSMContext, file_type: str):
        """Handle statement file upload"""
        try:
            current_state = await state.get_state()
            
            if current_state != AdminStates.waiting_for_statement:
                await message.answer("Please use /statement command to upload a bank statement.")
                return
            
            user_id = str(message.from_user.id)
            
            # Check if user is admin
            session = self.db_manager.get_session()
            admin = AdminOperations.get_admin_by_telegram_id(session, user_id)
            
            if not admin:
                await message.answer("⚠️ You need admin privileges to upload statements.")
                return
            
            # Download the file
            if file_type == "photo":
                file_obj = message.photo[-1]
                file_info = await self.bot.get_file(file_obj.file_id)
                file_extension = ".jpg"
            else:
                file_obj = message.document
                file_info = await self.bot.get_file(file_obj.file_id)
                file_extension = Path(file_obj.file_name).suffix if file_obj.file_name else ""
            
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"statement_{user_id}_{timestamp}{file_extension}"
            filepath = self.uploads_dir / filename
            
            # Download file
            await self.bot.download_file(file_info.file_path, str(filepath))
            
            await message.answer("📄 Processing bank statement... Please wait.")
            
            # Process the statement
            result = await self._process_statement(filepath, admin, session)
            
            if result['success']:
                await message.answer(
                    f"✅ Statement processed successfully!\n\n"
                    f"📊 **Results:**\n"
                    f"• Transactions found: {result['transaction_count']}\n"
                    f"• Total amount: ETB {result['total_amount']:,.2f}\n"
                    f"• Reconciliation completed\n\n"
                    f"📋 **Next Steps:**\n"
                    f"• Review reconciliation results\n"
                    f"• Generate audit report\n"
                    f"• Address any discrepancies"
                )
            else:
                await message.answer(f"❌ Error processing statement: {result['error']}")
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error handling statement file: {e}")
            await message.answer("Sorry, something went wrong while processing the statement. Please try again.")
            await state.clear()
        finally:
            session.close()
    
    async def _process_statement(self, filepath: Path, admin, session) -> Dict:
        """Process uploaded bank statement"""
        try:
            # Get recent transactions for reconciliation
            recent_transactions = session.query(Transaction).filter(
                Transaction.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Convert to list of dictionaries
            transactions_data = []
            for trans in recent_transactions:
                transactions_data.append({
                    'id': trans.id,
                    'stn_number': trans.stn_number,
                    'amount': trans.amount,
                    'transaction_date': trans.transaction_date,
                    'waiter_id': trans.waiter_id,
                    'bank_type': trans.bank_type.value
                })
            
            # Perform reconciliation
            reconciliation_result = self.audit_engine.reconcile_statements(
                transactions=transactions_data,
                bank_statement_path=str(filepath),
                bank_type='cbe'  # Default, could be made configurable
            )
            
            if reconciliation_result['success']:
                # Generate audit report
                report_path = self.audit_engine.generate_audit_report(
                    reconciliation_results=reconciliation_result['reconciliation_results'],
                    summary=reconciliation_result['summary'],
                    report_date=datetime.now(),
                    admin_name=admin.name
                )
                
                return {
                    'success': True,
                    'transaction_count': reconciliation_result['summary']['total_statement_entries'],
                    'total_amount': reconciliation_result['summary']['matched_amount'],
                    'report_path': report_path,
                    'reconciliation_results': reconciliation_result
                }
            else:
                return {
                    'success': False,
                    'error': reconciliation_result['error']
                }
                
        except Exception as e:
            logger.error(f"Error processing statement: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_callback(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Handle callback queries"""
        try:
            data = callback_query.data
            
            if data.startswith("view_"):
                await self._handle_view_callbacks(callback_query, data)
            elif data.startswith("report_"):
                await self._handle_report_callbacks(callback_query, data)
            elif data.startswith("upload_"):
                await self._handle_upload_callbacks(callback_query, data)
            elif data.startswith("manage_"):
                await self._handle_manage_callbacks(callback_query, data)
            else:
                await callback_query.answer("Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            await callback_query.answer("Sorry, something went wrong.")
    
    async def _handle_view_callbacks(self, callback_query: types.CallbackQuery, data: str):
        """Handle view-related callbacks"""
        if data == "view_transactions":
            await callback_query.answer("Loading transactions...")
            # This would trigger the transactions command
            await self.cmd_transactions(callback_query.message)
        elif data == "view_all_transactions":
            await callback_query.answer("Loading all transactions...")
            # Implementation for viewing all transactions
        elif data == "filter_transactions":
            await callback_query.answer("Filter options coming soon...")
        elif data == "export_transactions":
            await callback_query.answer("Exporting transactions...")
            # Implementation for exporting transactions
        elif data == "refresh_transactions":
            await callback_query.answer("Refreshing...")
            await self.cmd_transactions(callback_query.message)
    
    async def _handle_report_callbacks(self, callback_query: types.CallbackQuery, data: str):
        """Handle report-related callbacks"""
        await callback_query.answer("Generating report...")
        
        # Implementation for different report types
        if data == "report_today":
            await callback_query.message.answer("📊 Generating today's report...")
        elif data == "report_week":
            await callback_query.message.answer("📊 Generating weekly report...")
        elif data == "report_month":
            await callback_query.message.answer("📊 Generating monthly report...")
        elif data == "report_custom":
            await callback_query.message.answer("📊 Custom report options coming soon...")
        elif data == "report_fraud":
            await callback_query.message.answer("🔍 Generating fraud analysis report...")
        elif data == "report_performance":
            await callback_query.message.answer("📈 Generating performance report...")
    
    async def _handle_upload_callbacks(self, callback_query: types.CallbackQuery, data: str):
        """Handle upload-related callbacks"""
        if data == "upload_statement":
            await callback_query.answer("Redirecting to statement upload...")
            await self.cmd_statement(callback_query.message, FSMContext())
    
    async def _handle_manage_callbacks(self, callback_query: types.CallbackQuery, data: str):
        """Handle management-related callbacks"""
        if data == "manage_users":
            await callback_query.answer("Loading user management...")
            await self.cmd_waiters(callback_query.message)
        elif data == "add_waiter":
            await callback_query.answer("Add waiter feature coming soon...")
        elif data == "edit_waiter":
            await callback_query.answer("Edit waiter feature coming soon...")
        elif data == "waiter_stats":
            await callback_query.answer("Loading waiter statistics...")
        elif data == "refresh_waiters":
            await callback_query.answer("Refreshing...")
            await self.cmd_waiters(callback_query.message)
    
    async def handle_text(self, message: types.Message, state: FSMContext):
        """Handle text messages"""
        current_state = await state.get_state()
        
        if current_state == AdminStates.waiting_for_statement:
            await message.answer("Please upload a bank statement file (document or photo), not text.")
        else:
            await message.answer("Use /dashboard to view the system overview or /help for assistance.")
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Admin Bot...")
        await self.dp.start_polling(self.bot)


if __name__ == "__main__":
    # Setup logging
    logger.add("logs/admin_bot.log", rotation="1 day", retention="7 days")
    
    # Create and run bot
    bot = AdminBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        traceback.print_exc() 