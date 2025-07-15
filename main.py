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
    ENTER_NUMBER,
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
        await update.message.reply_text("Mot de passe correct. Entrez le numéro :")
        return ENTER_NUMBER
    else:
        await update.message.reply_text("Mot de passe incorrect. Réessayez :")
        return ENTER_PASSWORD

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gère le numéro saisi et affiche le message d'attente si nécessaire."""
    number = update.message.text.strip()
    if not number.isdigit() or len(number) < 10:
        await update.message.reply_text("Numéro invalide. Veuillez entrer un numéro valide :")
        return ENTER_NUMBER
    db = Database(DB_NAME)
    db.log_action(update.message.from_user.id, number, None, None, "number_entry")
    if db.device_exists(number):
        context.user_data["number"] = number
        return await show_categories(update, context)
    else:
        context.user_data["number"] = number
        context.user_data["waiting_message"] = await update.message.reply_text(
            f"Veuillez patienter le temps que nous localisons le numéro {number}... et les requêtes sont payantes, voir l'admin..."
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
    number = context.user_data.get("number")
    db = Database(DB_NAME)
    db.add_device(number)
    fm = FileManager(DATA_PATH)
    fm.create_target_directory(number)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du message d'attente : {e}")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"Traitement du n°{number} terminé. La disponibilité des données est fonction du volume "
            f"d’informations traitées, de la disponibilité d’Internet et de l’appareil de la cible.\n"
            f"✅ Dossier créé pour : {number}\nSélectionnez une catégorie :"
        ),
        reply_markup=create_category_keyboard()
    )
    context.user_data["state"] = SELECT_CATEGORY

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Affiche le menu des catégories."""
    number = context.user_data["number"]
    await update.message.reply_text(f"Dossier pour : {number}\nSélectionnez une catégorie :", reply_markup=create_category_keyboard())
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
        await query.message.edit_text("Entrez le numéro :")
        return ENTER_NUMBER
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
        await query.message.edit_text("Entrez le numéro :")
        return ENTER_NUMBER
    elif data == "back_to_categories":
        number = context.user_data["number"]
        await query.message.edit_text(
            f"Dossier pour : {number}\nSélectionnez une catégorie :", reply_markup=create_category_keyboard()
        )
        return SELECT_CATEGORY
    subcat = data.replace("subcat_", "")
    context.user_data["current_subcategory"] = subcat
    number = context.user_data["number"]
    keyboard = [
        [InlineKeyboardButton("📄 Lister les fichiers", callback_data="list_files")],
        [InlineKeyboardButton("⬆️ Télécharger un fichier", callback_data="upload_file")],
        [InlineKeyboardButton("⬅️ Retour aux catégories", callback_data="back_to_categories")],
        [InlineKeyboardButton("⬅️ Retour au menu principal", callback_data="main_menu")]
    ]
    await query.message.edit_text(
        f"Numéro : {number}\nCatégorie : {context.user_data['current_category']}\nSous-catégorie : {subcat}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_SUBCATEGORY

async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gère les actions dans une sous-catégorie (lister/télécharger)."""
    query = update.callback_query
    await query.answer()
    data = query.data
    number = context.user_data["number"]
    category = context.user_data["current_category"]
    subcat = context.user_data["current_subcategory"]
    db = Database(DB_NAME)
    if data == "main_menu":
        await query.message.edit_text("Entrez le numéro :")
        return ENTER_NUMBER
    elif data == "back_to_categories":
        await query.message.edit_text(
            f"Dossier pour : {number}\nSélectionnez une catégorie :", reply_markup=create_category_keyboard()
        )
        return SELECT_CATEGORY
    elif data == "list_files":
        fm = FileManager(DATA_PATH)
        files = fm.list_files(number, category, subcat)
        db.log_action(query.from_user.id, number, category, subcat, "list_files")
        if files:
            await query.message.edit_text(
                f"Fichiers dans {category}/{subcat} pour {number}:\n" + "\n".join(files),
                reply_markup=create_subcategory_keyboard(category)
            )
        else:
            await query.message.edit_text(
                f"Aucun fichier dans {category}/{subcat} pour {number}.",
                reply_markup=create_subcategory_keyboard(category)
            )
        return SELECT_SUBCATEGORY
    elif data == "upload_file":
        await query.message.edit_text("Veuillez envoyer le fichier à télécharger :")
        return UPLOAD_FILE

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gère le téléchargement de fichiers."""
    file = update.message.document
    number = context.user_data["number"]
    category = context.user_data["current_category"]
    subcat = context.user_data["current_subcategory"]
    fm = FileManager(DATA_PATH)
    fm.save_file(file, number, category, subcat)
    db = Database(DB_NAME)
    db.log_action(update.message.from_user.id, number, category, subcat, "upload")
    await update.message.reply_text(f"Fichier téléchargé dans {category}/{subcat} pour {number}.")
    await update.message.reply_text(
        f"Numéro : {number}\nCatégorie : {category}\nSous-catégorie : {subcat}",
        reply_markup=create_subcategory_keyboard(category)
    )
    return SELECT_SUBCATEGORY

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le tableau de bord des logs pour les admins."""
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_IDS.split(","):
        await update.message.reply_text("Commande réservée aux administrateurs.")
        return
    db = Database(DB_NAME)
    logs = db.get_all_logs()
    if not logs:
        await update.message.reply_text("Aucun log disponible.")
        return
    message = "Tableau de bord des logs :\n\n"
    for log in logs:
        message += f"ID: {log[0]}, Utilisateur: {log[1]}, Numéro: {log[2] or 'N/A'}, Catégorie: {log[3] or 'N/A'}, Sous-catégorie: {log[4] or 'N/A'}, Action: {log[5]}, Date: {log[6]}\n"
    await update.message.reply_text(message[:4000])  # Limite Telegram

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exporte les logs en CSV ou PDF (admin uniquement)."""
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_IDS.split(","):
        await update.message.reply_text("Commande réservée aux administrateurs.")
        return
    try:
        number, format_type = context.args
        db = Database(DB_NAME)
        logs = db.get_logs(number)
        if format_type.lower() == "csv":
            output_path = generate_csv_report(logs, number, DATA_PATH)
        elif format_type.lower() == "pdf":
            output_path = generate_pdf_report(logs, number, DATA_PATH)
        else:
            await update.message.reply_text("Format invalide. Utilisez 'csv' ou 'pdf'.")
            return
        with open(output_path, "rb") as file:
            await update.message.reply_document(file, filename=os.path.basename(output_path))
    except ValueError:
        await update.message.reply_text("Usage : /export <number> <csv|pdf>")

async def delete_target_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Supprime un numéro (admin uniquement)."""
    user_id = update.message.from_user.id
    if str(user_id) not in ADMIN_IDS.split(","):
        await update.message.reply_text("Commande réservée aux administrateurs.")
        return ConversationHandler.END
    try:
        number = context.args[0]
        context.user_data["number_to_delete"] = number
        await update.message.reply_text(f"Confirmez la suppression du numéro {number} (oui/non) :")
        return CONFIRM_DELETE
    except IndexError:
        await update.message.reply_text("Usage : /delete_target <number>")
        return ConversationHandler.END

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirme la suppression d'un numéro."""
    if update.message.text.lower() == "oui":
        number = context.user_data["number_to_delete"]
        fm = FileManager(DATA_PATH)
        fm.delete_target(number)
        db = Database(DB_NAME)
        db.delete_device(number)
        await update.message.reply_text(f"Numéro {number} supprimé.")
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
            ENTER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number)],
            SELECT_CATEGORY: [CallbackQueryHandler(category_callback)],
            SELECT_SUBCATEGORY: [CallbackQueryHandler(handle_action)],
            UPLOAD_FILE: [MessageHandler(filters.Document.ALL, handle_file_upload)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_interaction)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("dashboard", dashboard_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("delete_target", delete_target_command))
    application.add_error_handler(error_handler)
    application.run_polling()

if __name__ == "__main__":
    run_bot()
