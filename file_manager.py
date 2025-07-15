import os
import sqlite3
from mega import Mega
from config import DATA_PATH, DB_NAME, MEGA_EMAIL, MEGA_PASSWORD

# Initialisation du client MEGA
mega = Mega()
m = mega.login(MEGA_EMAIL, MEGA_PASSWORD)

def create_folder(path):
    """Crée un dossier sur MEGA si nécessaire"""
    try:
        relative_path = path.replace(DATA_PATH, '').lstrip('/')
        folders = relative_path.split('/')
        current_path = ''
        for folder in folders:
            current_path = f"{current_path}/{folder}" if current_path else f"/{folder}"
            existing_folders = m.get_files()
            if not any(f['a']['n'] == folder and f['t'] == 1 for f in existing_folders.values() if f['p'] == m.find(current_path.rsplit('/', 1)[0])[0] if current_path.count('/') > 1 else f['p'] == m.get_root_id()):
                m.create_folder(current_path)
        return True
    except Exception as e:
        print(f"Erreur lors de la création du dossier {path}: {str(e)}")
        return False

def create_device_folder(device_id):
    """Crée un dossier pour l'appareil sur MEGA"""
    folder_path = f"/{device_id}"
    try:
        folders = m.get_files()
        if not any(f['a']['n'] == device_id and f['t'] == 1 for f in folders.values()):
            m.create_folder(folder_path)
        return folder_path
    except Exception as e:
        print(f"Erreur lors de la création du dossier {folder_path}: {str(e)}")
        return None

def list_devices(data_path):
    """Liste tous les dossiers d'appareils sur MEGA"""
    try:
        folders = m.get_files()
        return [f['a']['n'] for f in folders.values() if f['t'] == 1 and f['p'] == m.get_root_id()]
    except Exception as e:
        print(f"Erreur lors du listage des dossiers: {str(e)}")
        return []

def list_files(category_path):
    """Liste les fichiers dans un dossier de catégorie sur MEGA"""
    try:
        relative_path = category_path.replace(DATA_PATH, '').lstrip('/')
        folder_id = m.find(relative_path)[0] if m.find(relative_path) else None
        if not folder_id:
            return []
        
        files = m.get_files_in_node(folder_id)
        return [f['a']['n'] for f in files.values() if f['t'] == 0]
    except Exception as e:
        print(f"Erreur lors du listage des fichiers dans {category_path}: {str(e)}")
        return []

def upload_file(file_path, local_path):
    """Enregistre un fichier sur MEGA"""
    try:
        relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
        folder_path = '/'.join(relative_path.split('/')[:-1])
        file_name = relative_path.split('/')[-1]
        
        # Créer les dossiers parents si nécessaire
        create_folder(os.path.join(DATA_PATH, folder_path))
        
        # Uploader le fichier
        m.upload(local_path, dest=m.find(folder_path)[0] if folder_path else None, dest_filename=file_name)
        return True
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du fichier {file_path}: {str(e)}")
        return False

def download_file(file_path, local_path):
    """Télécharge un fichier depuis MEGA"""
    try:
        relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
        file_id = m.find(relative_path)[0] if m.find(relative_path) else None
        if file_id:
            m.download(file_id, local_path)
            return True
        return False
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier {file_path}: {str(e)}")
        return False

def delete_device_folder(device_id):
    """Supprime le dossier d'un appareil sur MEGA"""
    try:
        folder_path = f"/{device_id}"
        folder_id = m.find(folder_path)[0] if m.find(folder_path) else None
        if folder_id:
            m.delete(folder_id)
            return True
        return False
    except Exception as e:
        print(f"Erreur lors de la suppression du dossier {device_id}: {str(e)}")
        return False

def log_activity(db_name, device_id, action, file_path):
    """Enregistre une activité dans la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT INTO logs (device_id, action, file_path) VALUES (?, ?, ?)", (device_id, action, file_path))
    conn.commit()
    conn.close()

def validate_device_id(device_id):
    """Valide le format de l'ID de l'appareil (IMEI, SN, ou numéro)"""
    import re
    # IMEI: 15 chiffres
    if re.match(r'^\d{15}$', device_id):
        return True
    # Numéro international: commence par +, suivi de 10-15 chiffres
    if re.match(r'^\+\d{10,15}$', device_id):
        return True
    # SN: alphanumérique, 5-20 caractères
    if re.match(r'^[a-zA-Z0-9]{5,20}$', device_id):
        return True
    return False
