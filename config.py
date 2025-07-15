import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]
DATA_PATH = os.environ.get('DATA_PATH', '/data')
DB_NAME = os.environ.get('DB_NAME', 'bot.db')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', 'your_password_here')
GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS', '')  # Base64-encoded credentials.json