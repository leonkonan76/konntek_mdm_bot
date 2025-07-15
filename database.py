import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name):
        """Initialise la connexion à la base de données SQLite."""
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Établit la connexion à la base de données."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données : {e}")
            raise

    def create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    device_id TEXT,
                    category TEXT,
                    subcategory TEXT,
                    action TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la création des tables : {e}")
            raise

    def device_exists(self, device_id):
        """Vérifie si un numéro existe dans la base de données."""
        try:
            self.cursor.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la vérification du numéro : {e}")
            return False

    def add_device(self, device_id):
        """Ajoute un nouveau numéro à la base de données."""
        try:
            self.cursor.execute("INSERT OR IGNORE INTO devices (device_id) VALUES (?)", (device_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'ajout du numéro : {e}")
            raise

    def delete_device(self, device_id):
        """Supprime un numéro de la base de données."""
        try:
            self.cursor.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
            self.cursor.execute("DELETE FROM logs WHERE device_id = ?", (device_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la suppression du numéro : {e}")
            raise

    def log_action(self, user_id, device_id, category, subcategory, action):
        """Enregistre une action dans la table des logs."""
        try:
            self.cursor.execute(
                "INSERT INTO logs (user_id, device_id, category, subcategory, action) VALUES (?, ?, ?, ?, ?)",
                (user_id, device_id, category, subcategory, action)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'enregistrement de l'action : {e}")
            raise

    def get_logs(self, device_id):
        """Récupère les logs pour un numéro donné."""
        try:
            self.cursor.execute("SELECT * FROM logs WHERE device_id = ?", (device_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération des logs : {e}")
            return []

    def get_all_logs(self):
        """Récupère tous les logs pour le tableau de bord."""
        try:
            self.cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de la récupération de tous les logs : {e}")
            return []

    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
