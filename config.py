import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]
DATA_PATH = os.environ.get('DATA_PATH', './data')  # Utilisé comme préfixe pour les chemins MEGA
DB_NAME = os.environ.get('DB_NAME', 'bot.db')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', 'your_password_here')
MEGA_EMAIL = os.environ.get('MEGA_EMAIL', 'your_mega_email_here')
MEGA_PASSWORD = os.environ.get('MEGA_PASSWORD', 'your_mega_password_here')
