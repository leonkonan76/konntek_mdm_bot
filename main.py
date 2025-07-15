import logging
     import os
     from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
     from telegram.ext import (
         Application,
         CommandHandler,
         MessageHandler,
         CallbackQueryHandler,
         ConversationHandler,
         ContextTypes,
         filters,
     )
     from config import BOT_TOKEN, BOT_PASSWORD, ADMIN_IDS, DATA_PATH, DB_NAME
     from database import Database
     from file_manager import FileManager
     from report_generator import generate_csv_report, generate_pdf_report

     # Configuration du logging
     logging.basicConfig(
         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
         level=logging.INFO
     )
     logger = logging.getLogger(__name__)

     # États de la conversation
     (
         ENTER_PASSWORD,
         ENTER_DEVICE_ID,
         SELECT_CATEGORY,
         SELECT_SUBCATEGORY,
         UPLOAD_FILE,
         CONFIRM_DELETE
     ) = range(6)

     # Catégories et sous-catégories
     CATEGORIES = {
         "📍 Localisation": ["GPS", "Historique des positions"],
         "📞 Appels & SMS": ["Journal d'appels", "Messages"],
         "🖼️ Photos & Vidéos": ["Photos", "Vidéos"],
         "📱 Applications": ["Applications installées", "Données des applications"],
         "🔒 Sécurité": ["Mots de passe", "Données chiffrées"],
         "🌐 Réseaux sociaux": ["WhatsApp", "Facebook", "Instagram", "Autres"],
     }

     async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Démarre la conversation et demande le mot de passe."""
         await update.message.reply_text("Veuillez entrer le mot de passe :")
         return ENTER_PASSWORD

     async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Vérifie le mot de passe saisi."""
         user_input = update.message.text
         if user_input == BOT_PASSWORD:
             await update.message.reply_text("Mot de passe correct. Entrez l'identifiant de l'appareil :")
             return ENTER_DEVICE_ID
         else:
             await update.message.reply_text("Mot de passe incorrect. Réessayez :")
             return ENTER_PASSWORD

     async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Gère l'identifiant de l'appareil et affiche le message d'attente si nécessaire."""
         device_id = update.message.text.strip()
         if not device_id.isdigit() or len(device_id) < 10:
             await update.message.reply_text("Identifiant invalide. Veuillez entrer un numéro valide :")
             return ENTER_DEVICE_ID
         db = Database(DB_NAME)
         if db.device_exists(device_id):
             context.user_data["device_id"] = device_id
             return await show_categories(update, context)
         else:
             context.user_data["device_id"] = device_id
             context.user_data["waiting_message"] = await update.message.reply_text(
                 f"Veuillez patienter le temps que nous localisons le numéro {device_id}... et les requêtes sont payantes, voir l'admin..."
             )
             context.job_queue.run_once(
                 end_waiting,
                 300,
                 data={"chat_id": update.message.chat_id, "message_id": context.user_data["waiting_message"].message_id},
                 chat_id=update.message.chat_id,
                 user_id=update.message.from_user.id
             )
             return ConversationHandler.END

     async def waiting_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
         """Gère les interactions pendant l'attente."""
         if "waiting_message" in context.user_data:
             await update.message.reply_text(
                 "⏳ Veuillez patienter, le traitement est en cours. Vous pouvez continuer à interagir avec le bot après la fin du traitement.\nUtilisez '/start' pour retourner au menu principal."
             )

     async def end_waiting(context: ContextTypes.DEFAULT_TYPE) -> None:
         """Supprime le message d'attente et affiche le menu des catégories."""
         job = context.job
         chat_id = job.data["chat_id"]
         message_id = job.data["message_id"]
         device_id = context.user_data.get("device_id")
         db = Database(DB_NAME)
         db.add_device(device_id)
         fm = FileManager(DATA_PATH)
         fm.create_target_directory(device_id)
         try:
             await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
         except Exception as e:
             logger.error(f"Erreur lors de la suppression du message d'attente : {e}")
         await context.bot.send_message(
             chat_id=chat_id,
             text=(
                 f"Traitement du n°{device_id} terminé. La disponibilité des données est fonction du volume "
                 f"d’informations traitées, de la disponibilité d’Internet et de l’appareil de la cible.\n"
                 f"✅ Dossier créé pour : {device_id}\nSélectionnez une catégorie :"
             ),
             reply_markup=create_category_keyboard()
         )
         context.user_data["state"] = SELECT_CATEGORY

     async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Affiche le menu des catégories."""
         await update.message.reply_text("Sélectionnez une catégorie :", reply_markup=create_category_keyboard())
         return SELECT_CATEGORY

     def create_category_keyboard():
         """Crée le clavier des catégories."""
         keyboard = [[InlineKeyboardButton(category, callback_data=f"category_{category}")] for category in CATEGORIES.keys()]
         keyboard.append([InlineKeyboardButton("⬅️ Retour au menu principal", callback_data="main_menu")])
         return InlineKeyboardMarkup(keyboard)

     async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Gère la sélection d'une catégorie."""
         query = update.callback_query
         await query.answer()
         data = query.data
         if data == "main_menu":
             await query.message.edit_text("Entrez l'identifiant de l'appareil :")
             return ENTER_DEVICE_ID
         category = data.replace("category_", "")
         context.user_data["current_category"] = category
         await query.message.edit_text(
             f"Catégorie : {category}\nSélectionnez une sous-catégorie :",
             reply_markup=create_subcategory_keyboard(category)
         )
         return SELECT_SUBCATEGORY

     def create_subcategory_keyboard(category):
         """Crée le clavier des sous-catégories."""
         keyboard = [[InlineKeyboardButton(subcat, callback_data=f"subcat_{subcat}")] for subcat in CATEGORIES[category]]
         keyboard.append([InlineKeyboardButton("⬅️ Retour aux catégories", callback_data="back_to_categories")])
         keyboard.append([InlineKeyboardButton("⬅️ Retour au menu principal", callback_data="main_menu")])
         return InlineKeyboardMarkup(keyboard)

     async def subcategory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Gère la sélection d'une sous-catégorie."""
         query = update.callback_query
         await query.answer()
         data = query.data
         if data == "main_menu":
             await query.message.edit_text("Entrez l'identifiant de l'appareil :")
             return ENTER_DEVICE_ID
         elif data == "back_to_categories":
             await query.message.edit_text("Sélectionnez une catégorie :", reply_markup=create_category_keyboard())
             return SELECT_CATEGORY
         subcat = data.replace("subcat_", "")
         context.user_data["current_subcategory"] = subcat
         device_id = context.user_data["device_id"]
         keyboard = [
             [InlineKeyboardButton("📄 Lister les fichiers", callback_data="list_files")],
             [InlineKeyboardButton("⬆️ Télécharger un fichier", callback_data="upload_file")],
             [InlineKeyboardButton("⬅️ Retour aux catégories", callback_data="back_to_categories")],
             [InlineKeyboardButton("⬅️ Retour au menu principal", callback_data="main_menu")]
         ]
         await query.message.edit_text(
             f"Appareil : {device_id}\nCatégorie : {context.user_data['current_category']}\nSous-catégorie : {subcat}",
             reply_markup=InlineKeyboardMarkup(keyboard)
         )
         return SELECT_SUBCATEGORY

     async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Gère les actions dans une sous-catégorie (lister/télécharger)."""
         query = update.callback_query
         await query.answer()
         data = query.data
         device_id = context.user_data["device_id"]
         category = context.user_data["current_category"]
         subcat = context.user_data["current_subcategory"]
         if data == "main_menu":
             await query.message.edit_text("Entrez l'identifiant de l'appareil :")
             return ENTER_DEVICE_ID
         elif data == "back_to_categories":
             await query.message.edit_text("Sélectionnez une catégorie :", reply_markup=create_category_keyboard())
             return SELECT_CATEGORY
         elif data == "list_files":
             fm = FileManager(DATA_PATH)
             files = fm.list_files(device_id, category, subcat)
             if files:
                 await query.message.edit_text(
                     f"Fichiers dans {category}/{subcat} pour {device_id}:\n" + "\n".join(files),
                     reply_markup=create_subcategory_keyboard(category)
                 )
             else:
                 await query.message.edit_text(
                     f"Aucun fichier dans {category}/{subcat} pour {device_id}.",
                     reply_markup=create_subcategory_keyboard(category)
                 )
             return SELECT_SUBCATEGORY
         elif data == "upload_file":
             await query.message.edit_text("Veuillez envoyer le fichier à télécharger :")
             return UPLOAD_FILE

     async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Gère le téléchargement de fichiers."""
         file = update.message.document
         device_id = context.user_data["device_id"]
         category = context.user_data["current_category"]
         subcat = context.user_data["current_subcategory"]
         fm = FileManager(DATA_PATH)
         fm.save_file(file, device_id, category, subcat)
         db = Database(DB_NAME)
         db.log_action(update.message.from_user.id, device_id, category, subcat, "upload")
         await update.message.reply_text(f"Fichier téléchargé dans {category}/{subcat} pour {device_id}.")
         await update.message.reply_text(
             f"Catégorie : {category}\nSélectionnez une sous-catégorie :",
             reply_markup=create_subcategory_keyboard(category)
         )
         return SELECT_SUBCATEGORY

     async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
         """Exporte les logs en CSV ou PDF (admin uniquement)."""
         user_id = update.message.from_user.id
         if str(user_id) not in ADMIN_IDS.split(","):
             await update.message.reply_text("Commande réservée aux administrateurs.")
             return
         try:
             device_id, format_type = context.args
             db = Database(DB_NAME)
             logs = db.get_logs(device_id)
             if format_type.lower() == "csv":
                 output_path = generate_csv_report(logs, device_id, DATA_PATH)
             elif format_type.lower() == "pdf":
                 output_path = generate_pdf_report(logs, device_id, DATA_PATH)
             else:
                 await update.message.reply_text("Format invalide. Utilisez 'csv' ou 'pdf'.")
                 return
             with open(output_path, "rb") as file:
                 await update.message.reply_document(file, filename=os.path.basename(output_path))
         except ValueError:
             await update.message.reply_text("Usage : /export <device_id> <csv|pdf>")

     async def delete_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Supprime un appareil (admin uniquement)."""
         user_id = update.message.from_user.id
         if str(user_id) not in ADMIN_IDS.split(","):
             await update.message.reply_text("Commande réservée aux administrateurs.")
             return ConversationHandler.END
         try:
             device_id = context.args[0]
             context.user_data["device_to_delete"] = device_id
             await update.message.reply_text(f"Confirmez la suppression de l'appareil {device_id} (oui/non) :")
             return CONFIRM_DELETE
         except IndexError:
             await update.message.reply_text("Usage : /delete_target <device_id>")
             return ConversationHandler.END

     async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
         """Confirme la suppression d'un appareil."""
         if update.message.text.lower() == "oui":
             device_id = context.user_data["device_to_delete"]
             fm = FileManager(DATA_PATH)
             fm.delete_target(device_id)
             db = Database(DB_NAME)
             db.delete_device(device_id)
             await update.message.reply_text(f"Appareil {device_id} supprimé.")
         else:
             await update.message.reply_text("Suppression annulée.")
         return ConversationHandler.END

     async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
         """Gère les erreurs."""
         logger.error("Erreur détaillée : %s", str(context.error), exc_info=True)
         if update and update.message:
             await update.message.reply_text("Une erreur est survenue. Veuillez réessayer.")

     def run_bot():
         """Démarre le bot."""
         logger.info("Démarrage de l'application avec python-telegram-bot 22.0")
         application = Application.builder().token(BOT_TOKEN).read_timeout(10).write_timeout(10).build()
         conv_handler = ConversationHandler(
             entry_points=[CommandHandler("start", start)],
             states={
                 ENTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
                 ENTER_DEVICE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)],
                 SELECT_CATEGORY: [CallbackQueryHandler(category_callback)],
                 SELECT_SUBCATEGORY: [CallbackQueryHandler(handle_action)],
                 UPLOAD_FILE: [MessageHandler(filters.Document.ALL, handle_file_upload)],
                 CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete)],
             },
             fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_interaction)],
             allow_reentry=True
         )
         application.add_handler(conv_handler)
         application.add_handler(CommandHandler("export", export_command))
         application.add_handler(CommandHandler("delete_target", delete_target_command))
         application.add_error_handler(error_handler)
         application.run_polling()

     if __name__ == "__main__":
         run_bot()
