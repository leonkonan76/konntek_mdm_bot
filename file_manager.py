import os
import sqlite3
import time
from datetime import datetime
from mega import Mega
from config import DATA_PATH, DB_NAME, MEGA_EMAIL, MEGA_PASSWORD

# Initialisation du client MEGA
def get_mega_client():
    try:
        mega = Mega()
        return mega.login(MEGA_EMAIL, MEGA_PASSWORD)
    except Exception as e:
        print(f"Erreur lors de la connexion à MEGA: {str(e)}")
        return None

mega_client = get_mega_client()

def retry_operation(func, max_attempts=3, delay=5):
    """Réessaie une opération MEGA en cas d'échec"""
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            time.sleep(delay)
    return None

def create_folder(path):
    """Crée un dossier sur MEGA si nécessaire"""
    try:
        def create():
            relative_path = path.replace(DATA_PATH, '').lstrip('/')
            folders = relative_path.split('/')
            current_folder = mega_client.get_files()
            parent_id = None
            for folder in folders:
                found = False
                for file_id, file_data in current_folder.items():
                    if file_data.get('t') == 1 and file_data.get('n') == folder and (parent_id is None or file_data.get('p') == parent_id):
                        parent_id = file_id
                        found = True
                        break
                if not found:
                    parent_id = mega_client.create_folder(folder, parent_id)['f'][0]['h']
                current_folder = mega_client.get_files()
            return True
        return retry_operation(create)
    except Exception as e:
        print(f"Erreur lors de la création du dossier {path}: {str(e)}")
        return False

def create_device_folder(device_id):
    """Crée un dossier pour l'appareil sur MEGA"""
    folder_path = f"/{device_id}"
    try:
        def create():
            folders = mega_client.get_files()
            for file_id, file_data in folders.items():
                if file_data.get('t') == 1 and file_data.get('n') == device_id and file_data.get('p') == mega_client.root_id:
                    return folder_path
            mega_client.create_folder(device_id, mega_client.root_id)
            return folder_path
        return retry_operation(create)
    except Exception as e:
        print(f"Erreur lors de la création du dossier {folder_path}: {str(e)}")
        return None

def list_devices(data_path):
    """Liste tous les dossiers d'appareils sur MEGA"""
    try:
        def list_dev():
            folders = mega_client.get_files()
            devices = []
            for file_id, file_data in folders.items():
                if file_data.get('t') == 1 and file_data.get('p') == mega_client.root_id:
                    devices.append(file_data.get('n'))
            return devices
        return retry_operation(list_dev)
    except Exception as e:
        print(f"Erreur lors du listage des dossiers: {str(e)}")
        return []

def list_files(category_path):
    """Liste les fichiers dans un dossier de catégorie sur MEGA"""
    try:
        def list_f():
            relative_path = category_path.replace(DATA_PATH, '').lstrip('/')
            folders = relative_path.split('/')
            current_folder = mega_client.get_files()
            parent_id = None
            for folder in folders:
                found = False
                for file_id, file_data in current_folder.items():
                    if file_data.get('t') == 1 and file_data.get('n') == folder and (parent_id is None or file_data.get('p') == parent_id):
                        parent_id = file_id
                        found = True
                        break
                if not found:
                    return []
                current_folder = mega_client.get_files()
            files = []
            for file_id, file_data in current_folder.items():
                if file_data.get('t') == 0 and file_data.get('p') == parent_id:
                    files.append(file_data.get('n'))
            return files
        return retry_operation(list_f)
    except Exception as e:
        print(f"Erreur lors du listage des fichiers dans {category_path}: {str(e)}")
        return []

def upload_file(file_path, local_path):
    """Enregistre un fichier sur MEGA"""
    try:
        def upload():
            relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
            folder_path = '/'.join(relative_path.split('/')[:-1])
            file_name = relative_path.split('/')[-1]
            create_folder(os.path.join(DATA_PATH, folder_path))
            folders = mega_client.get_files()
            parent_id = None
            for folder in folder_path.split('/'):
                found = False
                for file_id, file_data in folders.items():
                    if file_data.get('t') == 1 and file_data.get('n') == folder and (parent_id is None or file_data.get('p') == parent_id):
                        parent_id = file_id
                        found = True
                        break
                if not found:
                    return False
                folders = mega_client.get_files()
            mega_client.upload(local_path, parent_id, file_name)
            return True
        return retry_operation(upload)
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du fichier {file_path}: {str(e)}")
        return False

def download_file(file_path, local_path):
    """Télécharge un fichier depuis MEGA"""
    try:
        def download():
            relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
            file_name = relative_path.split('/')[-1]
            folder_path = '/'.join(relative_path.split('/')[:-1])
            folders = mega_client.get_files()
            parent_id = None
            for folder in folder_path.split('/'):
                found = False
                for file_id, file_data in folders.items():
                    if file_data.get('t') == 1 and file_data.get('n') == folder and (parent_id is None or file_data.get('p') == parent_id):
                        parent_id = file_id
                        found = True
                        break
                if not found:
                    return False
                folders = mega_client.get_files()
            for file_id, file_data in folders.items():
                if file_data.get('t') == 0 and file_data.get('n') == file_name and file_data.get('p') == parent_id:
                    mega_client.download(file_id, dest_path=local_path)
                    return True
            return False
        return retry_operation(download)
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier {file_path}: {str(e)}")
        return False

def delete_device_folder(device_id):
    """Supprime le dossier d'un appareil sur MEGA"""
    try:
        def delete():
            folders = mega_client.get_files()
            for file_id, file_data in folders.items():
                if file_data.get('t') == 1 and file_data.get('n') == device_id and file_data.get('p') == mega_client.root_id:
                    mega_client.delete(file_id)
                    return True
            return False
        return retry_operation(delete)
    except Exception as e:
        print(f"Erreur lors de la suppression du dossier {device_id}: {str(e)}")
        return False

def log_activity(db_name, device_id, action, file_path):
    """Enregistre une activité dans la base de données"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("INSERT INTO logs (device_id, action, file_path, timestamp) VALUES (?, ?, ?, ?)",
              (device_id, action, file_path, datetime.now()))
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
