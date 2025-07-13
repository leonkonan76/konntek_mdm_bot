# database.py
import sqlite3

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
    conn.commit()
    conn.close()

def add_device(db_name, device_id, device_type):
    """Ajoute un appareil"""
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
    """Supprime un appareil"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    conn.commit()
    conn.close()
