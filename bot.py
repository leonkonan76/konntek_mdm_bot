import os
import logging
import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN") or "ton_token_ici"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_PATH = "konntek_mdm.db"
DATA_ROOT = "data"

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifiant TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_target(target_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO targets (identifiant) VALUES (?)", (target_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur ajout cible DB : {e}")

def create_full_target_structure(target_id):
    base_path = os.path.join(DATA_ROOT, target_id)
    if not os.path.exists(base_path):
        structure = [
            "sms_mms/suivi", "sms_mms/alertes",
            # ... reste de la structure ...
        ]
        for path in structure:
            os.makedirs(os.path.join(base_path, path), exist_ok=True)
        return True
    return False

def get_main_menu(target_id):
    buttons = [
        [InlineKeyboardButton("1⃣ SMS / MMS", callback_data=f"{target_id}|sms_mms")],
        # ... autres boutons ...
    ]
    return InlineKeyboardMarkup(buttons)

def get_reply_menu():
    return ReplyKeyboardMarkup(
        [
            ["/stats", "/files"],
            ["/results", "/target"],
            ["/xdecryptor"]
        ], resize_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bienvenue sur Konntek MDM Bot 💻\n\nEntrez un numéro de téléphone, IMEI ou numéro de série.",
        reply_markup=get_reply_menu()
    )

async def handle_identifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = update.message.text.strip()
    if target_id.startswith("/"):
        return
    created = create_full_target_structure(target_id)
    add_target(target_id)
    msg = "📁 Dossier créé." if created else "📂 Dossier existant chargé."
    await update.message.reply_text(f"{msg} Pour identifiant : {target_id}")
    await update.message.reply_text("Choisissez une section :", reply_markup=get_main_menu(target_id))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        target_id, section = query.data.split("|")
        await query.edit_message_text(f"🔹 *{section.upper().replace('_', ' ')}* pour {target_id}", parse_mode="Markdown")
    except Exception as e:
        await query.message.reply_text(f"Erreur: {e}")

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_identifier))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("Bot lancé...")
    app.run_polling()
