# konntek_mdm_bot - Bot Telegram MDM avec base de données, menu interactif et admin sécurisé

import os
import logging
import sqlite3
import time

# Liste des administrateurs Telegram autorisés (à personnaliser)
ADMIN_IDS = [
  465520526  ]

telegram_available = True
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
except ModuleNotFoundError:
    print("⚠️ Module 'telegram' introuvable. Veuillez installer python-telegram-bot pour exécuter ce script.")
    telegram_available = False

# Configuration du bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PATH = "konntek_mdm.db"
DATA_ROOT = "data"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ... (le reste du code reste inchangé)

# Ajoutons aussi une commande /admin simple :
if telegram_available:
    async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ Accès refusé. Cette commande est réservée à l’administrateur.")
            return
        await update.message.reply_text("🔐 Panneau administrateur actif.\nUtilise /delete_target, /export, /stats_target...")

    # Dans __main__ : ajout du handler
    if __name__ == '__main__':
        init_db()
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CommandHandler("files", files))
        app.add_handler(CommandHandler("results", results))
        app.add_handler(CommandHandler("target", target))
        app.add_handler(CommandHandler("xdecryptor", xdecryptor))
        app.add_handler(CommandHandler("admin", admin))  # 🔐 Ajout admin ici

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_identifier))
        app.add_handler(CallbackQueryHandler(handle_button))

        print("Konntek MDM Bot actif...")
        app.run_polling()
