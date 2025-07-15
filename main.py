# main.py
import os
import logging
from datetime import datetime
import asyncio
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
from config import BOT_TOKEN, BOT_PASSWORD, ADMIN_IDS, DATA_PATH, DB_NAME
import telegram.error
import time

# Initialisation de la base de données
database.init_db(DB_NAME)

# Configuration des états de conversation
PASSWORD, MAIN_MENU, CATEGORY_SELECTION, SUBCATEGORY_SELECTION, FILE_OPERATION, WAITING = range(6)

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

# Claviers réutilisables
def get_main_category_keyboard():
    return [
        ["📱 SMS/MMS", "📞 Appels", "📍 Localisation"],
        ["🖼️ Photos & Vidéos", "💬 Messagerie instantanée", "🎙️ Contrôle à distance"],
        ["📺 Visualisation en direct", "📁 Gestionnaire de fichiers", "⏱ Restriction d'horaire"],
        ["📱 Applications", "🌐 Sites Web", "📅 Calendrier"],
        ["👤 Contacts", "📊 Outils d'analyse", "📋 Retour"]
    ]

def get_admin_keyboard():
    return [
        ["📋 Liste des cibles", "🗑️ Supprimer une cible"],
        ["📈 Statistiques", "📤 Exporter les logs"],
        ["📊 Tableau de bord", "⬅️ Retour au menu principal"]
    ]

async def return_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fonction utilitaire pour retourner au menu des catégories"""
    device_id = context.user_data.get('current_device')
    keyboard = get_main_category_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"Retour au menu des catégories pour {device_id}:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre ou réinitialise la conversation"""
    context.user_data.clear()
    await update.message.reply_text(
        "🔒 Veuillez entrer le mot de passe pour accéder au bot.",
        reply_markup=ReplyKeyboardRemove()
    )
    return PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie le mot de passe"""
    user_input = update.message.text.strip()
    if user_input == BOT_PASSWORD:
        for attempt in range(3):  # Retry up to 3 times
            try:
                await update.message.reply_text(
                    "✅ Mot de passe correct.\n"
                    "🔍 Entrez un IMEI, numéro de série (SN) ou numéro de téléphone (format international) pour commencer.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return MAIN_MENU
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)  # Wait before retrying
        await update.message.reply_text(
            "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Mot de passe incorrect. Veuillez réessayer ou utiliser /cancel pour annuler."
        )
        return PASSWORD

async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la saisie de l'identifiant de l'appareil"""
    try:
        user_id = update.effective_user.id
        user_input = update.message.text.strip()
        
        # Commande spéciale de réinitialisation
        if user_input.lower() == "/reset":
            return await start(update, context)
        
        if file_manager.validate_device_id(user_input):
            # Enregistrer la requête utilisateur
            database.log_user_request(DB_NAME, user_id, user_input)
            
            # Vérifier si le dossier existe déjà
            if user_input in file_manager.list_devices(DATA_PATH):
                context.user_data['current_device'] = user_input
                keyboard = get_main_category_keyboard()
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                for attempt in range(3):
                    try:
                        await update.message.reply_text(
                            f"✅ Accès direct au dossier existant : {user_input}\nSélectionnez une catégorie :",
                            reply_markup=reply_markup
                        )
                        return CATEGORY_SELECTION
                    except telegram.error.TimedOut:
                        logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                        await asyncio.sleep(2)
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
            
            # Créer le dossier si nécessaire
            try:
                device_path = file_manager.create_device_folder(user_input)
            except PermissionError as e:
                logger.error(f"Erreur de permission lors de la création du dossier: {str(e)}")
                await update.message.reply_text(
                    "❌ Erreur de permission lors de la création du dossier. Contactez l'administrateur."
                )
                return ConversationHandler.END
            
            context.user_data['current_device'] = user_input
            
            # Message d'attente
            for attempt in range(3):
                try:
                    waiting_message = await update.message.reply_text(
                        f"Veuillez patienter le temps que nous localisons le numéro {user_input}... "
                        "et les requêtes sont payantes, voir l'admin..."
                    )
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message d'attente, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            else:
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
            
            # Planifier la fin de l'attente
            logger.info("Planification de la fin d'attente pour device_id: %s", user_input)
            context.job_queue.run_once(
                callback=end_waiting,
                when=300,  # 5 minutes
                data={'device_id': user_input, 'chat_id': update.effective_chat.id},
                context=context
            )
            
            context.user_data['waiting_message_id'] = waiting_message.message_id
            context.user_data['waiting_start_time'] = datetime.now()
            
            return WAITING
        else:
            for attempt in range(3):
                try:
                    await update.message.reply_text(
                        "❌ Format invalide. Veuillez entrer un IMEI (15 chiffres), SN (alphanumérique) ou numéro international (ex: +33612345678)."
                    )
                    return MAIN_MENU
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            await update.message.reply_text(
                "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Erreur dans handle_device_id: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def end_waiting(context: ContextTypes.DEFAULT_TYPE):
    """Termine la période d'attente et affiche le menu"""
    job = context.job
    device_id = job.data['device_id']
    chat_id = job.data['chat_id']
    
    try:
        # Supprimer le message d'attente
        for attempt in range(3):
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=context.user_data.get('waiting_message_id')
                )
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de la suppression du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
        
        # Ajouter l'appareil à la base de données
        database.add_device(DB_NAME, device_id, "unknown")
        
        # Afficher le message de fin
        keyboard = get_main_category_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        for attempt in range(3):
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Traitement du n°{device_id} terminé. "
                         "La disponibilité des données est fonction du volume d’informations traitées, "
                         "de la disponibilité d’Internet et de l’appareil de la cible.\n"
                         f"✅ Dossier créé pour : {device_id}\nSélectionnez une catégorie :",
                    reply_markup=reply_markup
                )
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
        else:
            logger.error("Échec de l'envoi du message de fin après plusieurs tentatives")
            return ConversationHandler.END
        
        # Mettre à jour l'état
        context.user_data['current_device'] = device_id
        context.user_data.pop('waiting_message_id', None)
        context.user_data.pop('waiting_start_time', None)
        
        return CATEGORY_SELECTION
    except Exception as e:
        logger.error(f"Erreur dans end_waiting: {str(e)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Erreur critique. Utilisez /start pour réinitialiser."
        )
        return ConversationHandler.END

async def handle_waiting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les interactions pendant la période d'attente"""
    for attempt in range(3):
        try:
            await update.message.reply_text(
                "⏳ Veuillez patienter, le traitement est en cours. "
                "Vous pouvez continuer à interagir avec le bot après la fin du traitement."
            )
            return WAITING
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    await update.message.reply_text(
        "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
    )
    return ConversationHandler.END

async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection de catégorie principale"""
    try:
        category = update.message.text
        device_id = context.user_data.get('current_device')
        
        if not device_id:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
        
        # Gestion des commandes admin
        if category in ["📋 Liste des cibles", "🗑️ Supprimer une cible", "📈 Statistiques", "📤 Exporter les logs", "📊 Tableau de bord"]:
            return await admin_command(update, context)
        elif category == "⬅️ Retour au menu principal":
            return await start(update, context)
        
        # Gestion du retour
        if category == "📋 Retour":
            await update.message.reply_text(
                "🔍 Entrez un nouvel identifiant (IMEI, SN ou numéro) :",
                reply_markup=ReplyKeyboardRemove()
            )
            return MAIN_MENU
        
        # Vérifier si la catégorie existe dans la structure
        if category in MENU_STRUCTURE:
            context.user_data['current_main_category'] = category
            main_category = MENU_STRUCTURE[category]
            
            # Préparer le sous-menu
            submenu = main_category.get('submenu', [])
            if submenu:
                submenu_keyboard = []
                for i in range(0, len(submenu), 2):
                    submenu_keyboard.append(submenu[i:i+2])
                submenu_keyboard.append(["⬅️ Retour aux catégories", "⬅️ Retour au menu principal"])
                
                reply_markup = ReplyKeyboardMarkup(submenu_keyboard, resize_keyboard=True)
                
                for attempt in range(3):
                    try:
                        await update.message.reply_text(
                            f"🔽 Sous-catégories pour {category} :",
                            reply_markup=reply_markup
                        )
                        return SUBCATEGORY_SELECTION
                    except telegram.error.TimedOut:
                        logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                        await asyncio.sleep(2)
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
            else:
                return await handle_subcategory_selection(update, context, category, None)
        else:
            keyboard = get_main_category_keyboard()
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "❌ Catégorie non reconnue. Veuillez choisir une option valide :",
                reply_markup=reply_markup
            )
            return CATEGORY_SELECTION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_category_selection: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def handle_subcategory_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, subcategory=None):
    """Gère la sélection de sous-catégorie"""
    try:
        if not subcategory:
            subcategory = update.message.text
        
        device_id = context.user_data.get('current_device')
        main_category = context.user_data.get('current_main_category')
        
        if not device_id or not main_category:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
            
        # Gestion du retour
        if subcategory == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        elif subcategory == "⬅️ Retour au menu principal":
            return await start(update, context)
        
        # Vérifier si la sous-catégorie est valide
        main_category_data = MENU_STRUCTURE.get(main_category)
        if not main_category_data or subcategory not in main_category_data.get('submenu', []):
            await update.message.reply_text("❌ Sous-catégorie non valide. Veuillez réessayer.")
            return SUBCATEGORY_SELECTION
        
        # Déterminer le chemin du dossier
        main_folder = main_category_data['folder']
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
            file_keyboard.append(["⬆️ Télécharger un fichier"])
            file_keyboard.append(["⬅️ Retour aux catégories", "⬅️ Retour au menu principal"])
            reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
            
            for attempt in range(3):
                try:
                    await update.message.reply_text(
                        f"📂 Fichiers disponibles dans {subcategory}:\n"
                        "Sélectionnez un fichier pour le visualiser ou téléchargez-en un nouveau.",
                        reply_markup=reply_markup
                    )
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            else:
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
        else:
            reply_markup = ReplyKeyboardMarkup([
                ["⬆️ Télécharger un fichier"],
                ["⬅️ Retour aux catégories", "⬅️ Retour au menu principal"]
            ], resize_keyboard=True)
            for attempt in range(3):
                try:
                    await update.message.reply_text(
                        f"ℹ️ Aucun fichier dans {subcategory}.\n"
                        "Vous pouvez télécharger un fichier avec le bouton ci-dessous.",
                        reply_markup=reply_markup
                    )
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            else:
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
        
        return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_subcategory_selection: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def handle_file_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les opérations sur les fichiers dans une catégorie"""
    try:
        user_choice = update.message.text
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        
        if not device_id or not category_path:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
            
        if user_choice == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        elif user_choice == "⬅️ Retour au menu principal":
            return await start(update, context)
        elif user_choice == "⬆️ Télécharger un fichier":
            for attempt in range(3):
                try:
                    await update.message.reply_text(
                        "⬆️ Envoyez le fichier que vous souhaitez télécharger dans cette catégorie.",
                        reply_markup=ReplyKeyboardMarkup([
                            ["⬅️ Retour aux catégories", "⬅️ Retour au menu principal"]
                        ], resize_keyboard=True)
                    )
                    return FILE_OPERATION
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            await update.message.reply_text(
                "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
            )
            return ConversationHandler.END
        
        else:
            # Traitement de la sélection d'un fichier
            file_path = os.path.join(category_path, user_choice)
            
            if os.path.isfile(file_path):
                # Journaliser la consultation
                file_manager.log_activity(DB_NAME, device_id, "CONSULT", file_path)
                
                # Envoyer le fichier à l'utilisateur
                for attempt in range(3):
                    try:
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=open(file_path, 'rb'),
                            filename=user_choice
                        )
                        break
                    except telegram.error.TimedOut:
                        logger.warning(f"Timeout lors de l'envoi du fichier, tentative {attempt + 1}/3")
                        await asyncio.sleep(2)
                else:
                    await update.message.reply_text(
                        "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                    )
                    return ConversationHandler.END
                
                # Reafficher le menu des fichiers
                files = file_manager.list_files(category_path)
                file_keyboard = [[f] for f in files]
                file_keyboard.append(["⬆️ Télécharger un fichier"])
                file_keyboard.append(["⬅️ Retour aux catégories", "⬅️ Retour au menu principal"])
                reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
                
                for attempt in range(3):
                    try:
                        await update.message.reply_text(
                            "Sélectionnez une autre action:",
                            reply_markup=reply_markup
                        )
                        break
                    except telegram.error.TimedOut:
                        logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                        await asyncio.sleep(2)
                else:
                    await update.message.reply_text(
                        "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                    )
                    return ConversationHandler.END
            else:
                await update.message.reply_text("❌ Fichier introuvable. Veuillez choisir un fichier valide.")
            
            return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_file_operation: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le téléchargement de fichiers dans une catégorie"""
    try:
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        
        if not device_id or not category_path:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
            
        if update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)
            file_name = update.message.document.file_name
            
            # Sauvegarder le fichier
            file_path = os.path.join(category_path, file_name)
            await file.download_to_drive(file_path)
            
            # Journaliser l'upload
            file_manager.log_activity(DB_NAME, device_id, "UPLOAD", file_path)
            
            for attempt in range(3):
                try:
                    await update.message.reply_text(f"✅ Fichier {file_name} téléchargé avec succès.")
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
            else:
                await update.message.reply_text(
                    "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
                )
                return ConversationHandler.END
            
            # RETOUR AUTOMATIQUE AUX CATÉGORIES APRÈS TÉLÉCHARGEMENT
            return await return_to_categories(update, context)
        
        await update.message.reply_text("❌ Format de fichier non reconnu. Veuillez envoyer un document.")
        return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_file_upload: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le panel d'administration"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    for attempt in range(3):
        try:
            await update.message.reply_text(
                "🛠️ Panel Admin - Sélectionnez une option:",
                reply_markup=reply_markup
            )
            break
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    else:
        await update.message.reply_text(
            "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
        )
        return ConversationHandler.END
    
    return CATEGORY_SELECTION

async def list_targets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche la liste des cibles enregistrées"""
    targets = file_manager.list_devices(DATA_PATH)
    
    if targets:
        response = "📋 Cibles enregistrées:\n" + "\n".join([f"- {t}" for t in targets])
    else:
        response = "ℹ️ Aucune cible enregistrée."
    
    for attempt in range(3):
        try:
            await update.message.reply_text(response)
            break
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    else:
        await update.message.reply_text(
            "❌ Échec de connexion à Telegram après plusieurs tentatives. Veuillez réessayer plus tard."
        )
        return ConversationHandler.END
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    for attempt in range(3):
        try:
            await update.message.reply_text(
                "Sélectionnez une autre option:",
                reply_markup=reply_markup
            )
            break
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    return CATEGORY_SELECTION

async def delete_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime une cible spécifique"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    
    if not context.args:
        await update.message.reply_text("Usage: /delete_target <id>")
        return CATEGORY_SELECTION
    
    target_id = context.args[0]
    if file_manager.delete_device_folder(target_id):
        database.delete_device(DB_NAME, target_id)
        for attempt in range(3):
            try:
                await update.message.reply_text(f"✅ Cible {target_id} supprimée.")
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
    else:
        for attempt in range(3):
            try:
                await update.message.reply_text(f"❌ Erreur lors de la suppression de {target_id}.")
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    for attempt in range(3):
        try:
            await update.message.reply_text(
                "Sélectionnez une autre option:",
                reply_markup=reply_markup
            )
            break
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    return CATEGORY_SELECTION

async def export_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exporte les logs d'une cible spécifique"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    
    if not context.args:
        await update.message.reply_text("Usage: /export <id> [csv|pdf]")
        return CATEGORY_SELECTION
    
    target_id = context.args[0]
    format_type = context.args[1] if len(context.args) > 1 else "csv"
    
    try:
        if format_type == "csv":
            filename = report_generator.generate_csv(DB_NAME, target_id)
            for attempt in range(3):
                try:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(filename, 'rb'),
                        filename=f"{target_id}_logs.csv"
                    )
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du fichier CSV, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
        elif format_type == "pdf":
            filename = report_generator.generate_pdf(DB_NAME, target_id)
            for attempt in range(3):
                try:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(filename, 'rb'),
                        filename=f"{target_id}_report.pdf"
                    )
                    break
                except telegram.error.TimedOut:
                    logger.warning(f"Timeout lors de l'envoi du fichier PDF, tentative {attempt + 1}/3")
                    await asyncio.sleep(2)
        else:
            await update.message.reply_text("❌ Format non supporté. Utilisez 'csv' ou 'pdf'.")
            return CATEGORY_SELECTION
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {str(e)}")
        await update.message.reply_text("❌ Erreur lors de la génération du rapport.")
    
    # Reafficher le menu admin
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    for attempt in range(3):
        try:
            await update.message.reply_text(
                "Sélectionnez une autre option:",
                reply_markup=reply_markup
            )
            break
        except telegram.error.TimedOut:
            logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
            await asyncio.sleep(2)
    return CATEGORY_SELECTION

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le tableau de bord des requêtes utilisateurs"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return ConversationHandler.END
    
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, device_id, timestamp FROM user_requests ORDER BY timestamp DESC")
        requests = c.fetchall()
        conn.close()
        
        if requests:
            response = "📊 Tableau de bord des requêtes:\n\n"
            for req in requests:
                response += f"Utilisateur ID: {req[0]}\nCible: {req[1]}\nDate: {req[2]}\n---\n"
        else:
            response = "ℹ️ Aucune requête enregistrée."
        
        for attempt in range(3):
            try:
                await update.message.reply_text(response)
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
        
        # Reafficher le menu admin
        keyboard = get_admin_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        for attempt in range(3):
            try:
                await update.message.reply_text(
                    "Sélectionnez une autre option:",
                    reply_markup=reply_markup
                )
                break
            except telegram.error.TimedOut:
                logger.warning(f"Timeout lors de l'envoi du message, tentative {attempt + 1}/3")
                await asyncio.sleep(2)
        return CATEGORY_SELECTION
    
    except Exception as e:
        logger.error(f"Erreur dans dashboard: {str(e)}")
        await update.message.reply_text("❌ Erreur lors de l'affichage du tableau de bord.")
        return CATEGORY_SELECTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule la conversation et réinitialise complètement"""
    context.user_data.clear()
    await update.message.reply_text(
        "✅ Opération annulée. Tapez /start pour recommencer.",
        reply_markup=ReplyKeyboardRemove()
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
            await update.message.reply_text(
                "❌ Une erreur critique s'est produite. "
                "Veuillez utiliser /start pour réinitialiser le bot.\n\n"
                f"Erreur: {str(context.error)[:200]}"
            )
        except:
            logger.error("Échec d'envoi du message d'erreur")
    
    return ConversationHandler.END

def run_bot():
    """Démarre le bot avec une gestion robuste"""
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(10).write_timeout(10).job_queue(True).build()
    
    application.add_handler(CommandHandler('reset', reset_command))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)
            ],
            WAITING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_waiting)
            ],
            CATEGORY_SELECTION: [
                MessageHandler(filters.Regex(r'^(📋 Liste des cibles|🗑️ Supprimer une cible|📈 Statistiques|📤 Exporter les logs|📊 Tableau de bord|⬅️ Retour au menu principal)$'), admin_command),
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
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start),
            CommandHandler('reset', reset_command)
        ]
    )
    
    # Commandes admin
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('delete_target', delete_target))
    application.add_handler(CommandHandler('export', export_logs))
    application.add_handler(CommandHandler('dashboard', dashboard))
    application.add_handler(conv_handler)
    
    # Gestion des erreurs
    application.add_error_handler(error_handler)
    
    logger.info("Bot démarré avec succès!")
    application.run_polling(timeout=20)  # Augmenter le timeout de polling

if __name__ == '__main__':
    run_bot()
