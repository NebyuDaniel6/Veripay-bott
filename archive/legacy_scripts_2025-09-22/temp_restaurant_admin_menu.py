    async def show_restaurant_admin_menu(self, update: Update, context=None):
        """Show Restaurant Admin menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("📊 My Restaurant Transactions", callback_data="restaurant_transactions")],
            [InlineKeyboardButton("📈 Daily Summary", callback_data="restaurant_daily_summary")],
            [InlineKeyboardButton("📤 Export CSV", callback_data="restaurant_export_csv")],
            [InlineKeyboardButton("🏦 Upload Bank Statement", callback_data="restaurant_upload_statement")],
            [InlineKeyboardButton("📋 Reconciliation Report", callback_data="restaurant_reconciliation")],
            [InlineKeyboardButton("👥 Pending Waiter Approvals", callback_data="restaurant_pending_waiters")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "��‍💼 **Restaurant Admin Panel** 👨‍💼\n\nSelect an option:"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
