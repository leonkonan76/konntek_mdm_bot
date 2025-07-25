# config.py
import os

# Token du bot Telegram
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Mot de passe pour accéder au bot
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', '')

# IDs des administrateurs
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]

# Chemins de données
DATA_PATH = os.environ.get('DATA_PATH', './data')
DB_NAME = os.environ.get('DB_NAME', 'mdm_bot.db')

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN n'est pas configuré")
if not BOT_PASSWORD:
    raise ValueError("BOT_PASSWORD n'est pas configuré")
if not ADMIN_IDS:
    print("Avertissement: Aucun ID administrateur configuré")
