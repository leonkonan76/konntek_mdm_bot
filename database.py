# database.py
import sqlite3
from datetime import datetime

def init_db(db_name):
    """Initialise la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    # Table appareils
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (id TEXT PRIMARY KEY, 
                  type TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    # Table logs
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id TEXT, 
                  action TEXT, 
                  file_path TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(device_id) REFERENCES devices(id))''')
                  
    # Table user_access
    c.execute('''CREATE TABLE IF NOT EXISTS user_access
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    conn.commit()
    conn.close()

def add_device(db_name, device_id, device_type):
    """Ajoute un appareil à la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO devices (id, type) VALUES (?, ?)", (device_id, device_type))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Existe déjà
    finally:
        conn.close()

def delete_device(db_name, device_id):
    """Supprime un appareil de la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    c.execute("DELETE FROM logs WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()

def log_user_access(db_name, user_id, action):
    """Journalise l'accès ou les actions des utilisateurs"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT INTO user_access (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()
    conn.close()

def get_user_access_logs(db_name):
    """Récupère les logs d'accès des utilisateurs"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT user_id, action, timestamp FROM user_access ORDER BY timestamp DESC")
    logs = c.fetchall()
    conn.close()
    return logs
