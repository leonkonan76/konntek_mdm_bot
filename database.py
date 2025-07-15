import sqlite3
from datetime import datetime

def init_db(db_name):
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    # Table pour les appareils
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (device_id TEXT PRIMARY KEY, name TEXT, created_at TIMESTAMP)''')
    
    # Table pour les logs d'accès utilisateur
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  device_id TEXT,
                  action TEXT,
                  file_path TEXT,
                  timestamp TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def add_device(db_name, device_id, name):
    """Ajoute un appareil à la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO devices (device_id, name, created_at) VALUES (?, ?, ?)",
              (device_id, name, datetime.now()))
    conn.commit()
    conn.close()

def delete_device(db_name, device_id):
    """Supprime un appareil de la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
    c.execute("DELETE FROM logs WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()

def log_user_access(db_name, user_id, action):
    """Enregistre l'accès utilisateur dans la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, timestamp) VALUES (?, ?, ?)",
              (user_id, action, datetime.now()))
    conn.commit()
    conn.close()
