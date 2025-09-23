    async def show_waiter_menu(self, update: Update, context=None):
        """Show Waiter menu - PRD compliant"""
        keyboard = [
            [InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")],
            [InlineKeyboardButton("📊 My Transactions", callback_data="waiter_my_transactions")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="waiter_help")],
            [InlineKeyboardButton("🚪 Sign Out", callback_data="sign_out")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🍳 **Waiter Panel** 🍳\n\nSelect an option:"
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
