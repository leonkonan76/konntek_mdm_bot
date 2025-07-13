import os

# Lire le token depuis les variables d'environnement
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]

# Chemin du dossier data
DATA_PATH = "./data"
DB_NAME = "mdm_bot.db"

# Vérification (pour debug)
if not BOT_TOKEN:
    print("ATTENTION: BOT_TOKEN n'est pas configuré!")
