import logging
import os
from io import BytesIO
from typing import Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from bot_v2.state import StateStore
from bot_v2.storage import Storage
from bot_v2.ocr import VisionOCR

logger = logging.getLogger(__name__)

BANK_BUTTONS = [
    ("🏦 CBE", "bank_cbe"),
    ("📱 Telebirr", "bank_telebirr"),
    ("🏦 Dashen", "bank_dashen"),
    ("🏦 Abyssinia", "bank_abyssinia"),
]

state = StateStore()
storage: Storage
ocr: VisionOCR

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state.set_role(user.id, "waiter" if str(user.id) != os.environ.get("SUPER_ADMIN_ID", "") else "super_admin")
    buttons = [[InlineKeyboardButton("📸 Capture Payment", callback_data="capture_payment")]]
    if update.message:
        await update.message.reply_text("Welcome to VeriPay. Use menu buttons.", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "capture_payment":
        kb = [[InlineKeyboardButton(txt, callback_data=cb)] for (txt, cb) in BANK_BUTTONS]
        kb.append([InlineKeyboardButton("Other", callback_data="bank_other")])
        state.set_step(user_id, "waiting_bank")
        await query.edit_message_text("Select bank:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if query.data.startswith("bank_"):
        mapping = {
            "bank_cbe": "Commercial Bank of Ethiopia",
            "bank_telebirr": "Telebirr",
            "bank_dashen": "Dashen Bank",
            "bank_abyssinia": "Bank of Abyssinia",
            "bank_other": "Unknown",
        }
        chosen = mapping.get(query.data, "Unknown")
        state.set_bank(user_id, chosen)
        state.set_step(user_id, "waiting_receipt")
        await query.edit_message_text(f"✅ Bank selected: {chosen}\n\n📸 Now upload a clear receipt photo.")
        return

    if query.data == "view_full_ocr":
        # show last OCR stored in state
        user_id = update.effective_user.id
        full_text = state.get_last_ocr_text(user_id) or "(no OCR text)"
        await query.edit_message_text(full_text[:3900])
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if state.get_step(user_id) != "waiting_receipt":
        await update.message.reply_text("Please use the menu to start: tap 📸 Capture Payment.")
        return
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    bio = BytesIO()
    await file.download_to_memory(out=bio)
    image_bytes = bio.getvalue()
    bank_hint = state.get_bank(user_id)
    data = ocr.extract(image_bytes, bank_hint=bank_hint) or {}

    # store full OCR text
    full_text = data.get("raw_text")
    if full_text:
        state.set_last_ocr_text(user_id, full_text)

    bank = data.get("bank", "Unknown")
    amount = data.get("amount", "Unknown")
    sender = data.get("sender", "Unknown")
    time_val = data.get("time", "Unknown")
    ref = data.get("reference")

    parts = [
        f"✅ Captured",
        f"- Bank: {bank}",
        f"- Amount: {amount} ETB" if amount != "Unknown" else "- Amount: Unknown",
        f"- Sender: {sender if sender else 'Unknown'}",
        f"- Time: {time_val if time_val else 'Unknown'}",
    ]
    if ref:
        parts.append(f"- Ref: {ref}")

    kb = [[InlineKeyboardButton("🔎 View Full OCR", callback_data="view_full_ocr")]]
    await update.message.reply_text("\n".join(parts), reply_markup=InlineKeyboardMarkup(kb))
    state.set_step(user_id, None)

def create_application(token: str):
    app = ApplicationBuilder().token(token).build()
    global storage, ocr
    storage = Storage(os.environ.get("DATABASE_URL", "sqlite:///veripay_dev.db"))
    ocr = VisionOCR()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    app = create_application(token)
    print("Bot is running! Press Ctrl+C to stop.")
    app.run_polling()
