"""M2 Reconciliation Handler - Completely separate from M1"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from reconciliation import reconciler
import PyPDF2
import io

logger = logging.getLogger(__name__)

async def handle_upload_statement(update: Update):
    """Handle upload statement button - M2 only"""
    try:
        instructions = """📄 **Upload Bank Statement** 📄

To reconcile your transactions:

1️⃣ **Upload your weekly bank statement PDF**
2️⃣ **The bot will extract transaction references**
3️⃣ **Compare with waiter transactions**
4️⃣ **Show reconciliation results**

**Supported formats:**
• PDF bank statements
• Transaction reference numbers
• Ethiopian bank formats (CBE, Dashen, Abyssinia, Telebirr)

**Just upload your PDF now!** 📎"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Menu", callback_data="back_to_restaurant_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=instructions,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info("M2: Upload statement instructions shown")
        
    except Exception as e:
        logger.error(f"M2: Error showing upload instructions: {e}")
        await update.callback_query.answer("❌ Error showing instructions")

async def handle_document_upload(update: Update, context):
    """Handle PDF document uploads for reconciliation - M2 only"""
    try:
        user_id = update.effective_user.id
        document = update.message.document
        
        # Check if it's a PDF
        if not document.mime_type == 'application/pdf':
            await update.message.reply_text("❌ Please upload a PDF file.")
            return
        
        # Download the PDF
        file = await context.bot.get_file(document.file_id)
        pdf_bytes = await file.download_as_bytearray()
        
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
        
        # Extract references from PDF
        bank_refs = reconciler.parser.extract_references(pdf_text)
        
        if not bank_refs:
            await update.message.reply_text("❌ No transaction references found in the PDF. Please check the format.")
            return
        
        # For now, just show what we found
        result_text = f"""📊 **PDF Analysis Results**

**Found {len(bank_refs)} transaction references:**
{', '.join(list(bank_refs)[:10])}
{'...' if len(bank_refs) > 10 else ''}

**Note:** Full reconciliation requires database integration.
This is M2 working separately from M1! 🎉"""
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
        logger.info(f"M2: Processed PDF with {len(bank_refs)} references")
        
    except Exception as e:
        logger.error(f"M2: Error processing PDF: {e}")
        await update.message.reply_text(f"❌ Error processing PDF: {e}")

async def handle_reconciliation(update: Update):
    """Handle reconciliation button - M2 only"""
    try:
        result_text = """🔄 **Reconciliation Status**

**M2 Feature is working!** ✅

This button is now functional and separate from M1.

**Next steps:**
1. Upload a PDF bank statement
2. System will extract transaction references
3. Compare with waiter transactions
4. Show reconciliation results

**M2 is ready for testing!** 🚀"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Restaurant Menu", callback_data="back_to_restaurant_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=result_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info("M2: Reconciliation status shown")
        
    except Exception as e:
        logger.error(f"M2: Error showing reconciliation: {e}")
        await update.callback_query.answer("❌ Error showing reconciliation")
