    async def show_super_admin_menu(self, update: Update, context=None):
        """Show Super Admin menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("⏳ Pending Restaurant Approvals", callback_data="admin_pending_restaurants")],
            [InlineKeyboardButton("📊 All Transactions", callback_data="admin_all_transactions")],
            [InlineKeyboardButton("📊 Daily Report", callback_data="admin_daily_report")],
            [InlineKeyboardButton("🏦 Bank Statement Upload", callback_data="admin_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="admin_reconciliation_report")],
            [InlineKeyboardButton("👥 Manage Restaurants", callback_data="admin_manage_restaurants")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🔧 **Super Admin Panel** 🔧\n\nSelect an option:"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
