# file_manager.py
import os
import re
import shutil
import sqlite3
from datetime import datetime
from config import DATA_PATH, DB_NAME

def validate_device_id(input_str):
    """Valide un identifiant d'appareil"""
    patterns = [
        r'^\d{15}$',  # IMEI
        r'^\w{5,20}$',  # SN
        r'^\+\d{6,15}$'  # Numéro international
    ]
    return any(re.match(p, input_str) for p in patterns)

def create_device_folder(device_id):
    """Crée l'arborescence pour un nouvel appareil"""
    base_path = os.path.join(DATA_PATH, device_id)
    os.makedirs(base_path, exist_ok=True)
    
    # Créer les sous-dossiers principaux
    subfolders = [
        'sms_mms', 'appels', 'localisations', 'photos', 'messageries',
        'controle_distance', 'visualisation_directe', 'fichiers',
        'restrictions', 'applications', 'sites_web', 'calendrier',
        'contacts', 'analyse', 'logs'
    ]
    
    for folder in subfolders:
        os.makedirs(os.path.join(base_path, folder), exist_ok=True)
    
    return base_path

def delete_device_folder(device_id):
    """Supprime un dossier d'appareil"""
    try:
        base_path = os.path.join(DATA_PATH, device_id)
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
            return True
        return False
    except Exception as e:
        print(f"Erreur suppression: {e}")
        return False

def list_devices(data_path):
    """Liste tous les appareils enregistrés"""
    try:
        return [d for d in os.listdir(data_path) 
                if os.path.isdir(os.path.join(data_path, d)) and validate_device_id(d)]
    except FileNotFoundError:
        os.makedirs(data_path, exist_ok=True)
        return []

def list_files(directory):
    """Liste les fichiers dans un répertoire"""
    try:
        return [f for f in os.listdir(directory) 
                if os.path.isfile(os.path.join(directory, f))]
    except FileNotFoundError:
        return []

def log_activity(db_name, device_id, action, file_path=None):
    """Journalise une activité"""
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute(
            "INSERT INTO logs (device_id, action, file_path) VALUES (?, ?, ?)",
            (device_id, action, file_path)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur journalisation: {e}")
        return False
