# bot.py — Version corrigée pour PTB v20.8 et Python 3.11+

import os
import logging
import sqlite3
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PATH = "konntek_mdm.db"
DATA_ROOT = "data"
# Vérification que le token existe
if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN est vide ou non défini. Vérifie Render > Environment.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation base de données
def init_db(retry=3):
    for attempt in range(retry):
        try:
            conn = sqlite3.connect(DATABASE_PATH, timeout=5)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifiant TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError as e:
            logger.warning(f"Tentative {attempt+1}/{retry} - Erreur SQLite: {e}")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            break

# Ajout cible
def add_target(target_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO targets (identifiant) VALUES (?)", (target_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erreur ajout cible DB : {e}")

# Création de dossiers MDM
def create_full_target_structure(target_id):
    base_path = os.path.join(DATA_ROOT, target_id)
    if not os.path.exists(base_path):
        structure = [
            "sms_mms/suivi", "sms_mms/alertes",
            "appels/journaux", "appels/enregistrements", "appels/blocages",
            "localisations/historique", "localisations/temps_reel",
            "photos/images",
            "messageries/whatsapp", "messageries/facebook_messenger", "messageries/skype",
            "messageries/hangouts", "messageries/line", "messageries/kik",
            "messageries/viber", "messageries/gmail", "messageries/tango",
            "messageries/snapchat", "messageries/telegram",
            "controle_distance/audio_enregistrement", "controle_distance/prise_photo",
            "controle_distance/commandes_sms", "controle_distance/autres",
            "visualisation_directe/audio", "visualisation_directe/video", "visualisation_directe/capture_ecran",
            "fichiers/explorateur",
            "restrictions/horaires",
            "applications/installees", "applications/bloquees",
            "sites_web/historique", "sites_web/blocages",
            "calendrier/evenements",
            "contacts/nouveaux",
            "analyse/statistiques", "analyse/rapports/pdf", "analyse/rapports/excel", "analyse/rapports/csv"
        ]
        for path in structure:
            os.makedirs(os.path.join(base_path, path), exist_ok=True)
        return True
    return False

# Menus
def get_main_menu(target_id):
    buttons = [
        [InlineKeyboardButton("1⃣ SMS / MMS", callback_data=f"{target_id}|sms_mms")],
        [InlineKeyboardButton("2⃣ Appels", callback_data=f"{target_id}|appels")],
        [InlineKeyboardButton("3⃣ Localisations", callback_data=f"{target_id}|localisations")],
        [InlineKeyboardButton("4⃣ Photos", callback_data=f"{target_id}|photos")],
        [InlineKeyboardButton("5⃣ Messageries", callback_data=f"{target_id}|messageries")],
        [InlineKeyboardButton("6⃣ Contrôle à distance", callback_data=f"{target_id}|controle_distance")],
        [InlineKeyboardButton("7⃣ Visualisation directe", callback_data=f"{target_id}|visualisation_directe")],
        [InlineKeyboardButton("8⃣ Fichiers", callback_data=f"{target_id}|fichiers")],
        [InlineKeyboardButton("9⃣ Restrictions", callback_data=f"{target_id}|restrictions")],
        [InlineKeyboardButton("🔹 Applications", callback_data=f"{target_id}|applications")],
        [InlineKeyboardButton("🔗 Sites Web", callback_data=f"{target_id}|sites_web")],
        [InlineKeyboardButton("🗓️ Calendrier", callback_data=f"{target_id}|calendrier")],
        [InlineKeyboardButton("👥 Contacts", callback_data=f"{target_id}|contacts")],
        [InlineKeyboardButton("📊 Analyse", callback_data=f"{target_id}|analyse")],
    ]
    return InlineKeyboardMarkup(buttons)

def get_reply_menu():
    return ReplyKeyboardMarkup(
        [
            ["/stats", "/files"],
            ["/results", "/target"],
            ["/xdecryptor"]
        ], resize_keyboard=True
    )

# Commandes
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bienvenue sur Konntek MDM Bot 💻\n\nEntrez un numéro de téléphone, IMEI ou numéro de série pour accéder à la médiathèque associée.",
        reply_markup=get_reply_menu()
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 État général du système en cours...")

async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 Fichiers en cours de téléchargement...")

async def results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Résultats et journaux disponibles")

async def target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT identifiant FROM targets ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            txt = "📲 Cibles traitées :\n" + "\n".join(f"- {r[0]}" for r in rows)
            await update.message.reply_text(txt)
        else:
            await update.message.reply_text("Aucune cible enregistrée.")
    except Exception as e:
        await update.message.reply_text(f"Erreur lors de la lecture des cibles : {e}")

async def xdecryptor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Lancement du lecteur de fichier X-Decryptor...")

async def handle_identifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = update.message.text.strip()
    if target_id.startswith("/"):
        return
    created = create_full_target_structure(target_id)
    add_target(target_id)
    msg = "📁 Dossier créé." if created else "📂 Dossier existant chargé."
    await update.message.reply_text(f"{msg} Pour identifiant : {target_id}")
    await update.message.reply_text("Choisissez une section à explorer :", reply_markup=get_main_menu(target_id))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        target_id, section = query.data.split("|")
        await query.edit_message_text(f"🔹 *{section.upper().replace('_', ' ')}* pour {target_id}", parse_mode="Markdown")
    except:
        await query.message.reply_text("Erreur lors du traitement du menu.")

# Exécution
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("files", files))
    app.add_handler(CommandHandler("results", results))
    app.add_handler(CommandHandler("target", target))
    app.add_handler(CommandHandler("xdecryptor", xdecryptor))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_identifier))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("Konntek MDM Bot actif...")
    app.run_polling()
