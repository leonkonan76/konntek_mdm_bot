import os
import sqlite3
import base64
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from config import DATA_PATH, DB_NAME, GOOGLE_CREDENTIALS
import io

# Initialisation du client Google Drive
def get_drive_service():
    try:
        creds = None
        token_path = 'token.json'
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive.file'])
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if GOOGLE_CREDENTIALS:
                    credentials_json = base64.b64decode(GOOGLE_CREDENTIALS).decode('utf-8')
                    with open('credentials.json', 'w') as f:
                        f.write(credentials_json)
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/drive.file'])
                creds = flow.run_local_server(port=8080)
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Erreur lors de la connexion à Google Drive: {str(e)}")
        return None

drive_service = get_drive_service()

def retry_operation(func, max_attempts=3, delay=5):
    """Réessaie une opération Google Drive en cas d'échec"""
    import time
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            time.sleep(delay)
    return None

def create_folder(path):
    """Crée un dossier sur Google Drive si nécessaire"""
    try:
        def create():
            relative_path = path.replace(DATA_PATH, '').lstrip('/')
            folders = relative_path.split('/')
            parent_id = 'root'
            for folder in folders:
                query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
                results = drive_service.files().list(q=query, fields="files(id, name)").execute()
                files = results.get('files', [])
                if files:
                    parent_id = files[0]['id']
                else:
                    file_metadata = {
                        'name': folder,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_id]
                    }
                    file = drive_service.files().create(body=file_metadata, fields='id').execute()
                    parent_id = file.get('id')
            return True
        return retry_operation(create)
    except Exception as e:
        print(f"Erreur lors de la création du dossier {path}: {str(e)}")
        return False

def create_device_folder(device_id):
    """Crée un dossier pour l'appareil sur Google Drive"""
    try:
        def create():
            query = f"name='{device_id}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            if files:
                return f"/{device_id}"
            file_metadata = {
                'name': device_id,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': ['root']
            }
            file = drive_service.files().create(body=file_metadata, fields='id').execute()
            return f"/{device_id}"
        return retry_operation(create)
    except Exception as e:
        print(f"Erreur lors de la création du dossier {device_id}: {str(e)}")
        return None

def list_devices(data_path):
    """Liste tous les dossiers d'appareils sur Google Drive"""
    try:
        def list_dev():
            query = "mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(name)").execute()
            return [file['name'] for file in results.get('files', [])]
        return retry_operation(list_dev)
    except Exception as e:
        print(f"Erreur lors du listage des dossiers: {str(e)}")
        return []

def list_files(category_path):
    """Liste les fichiers dans un dossier de catégorie sur Google Drive"""
    try:
        def list_f():
            relative_path = category_path.replace(DATA_PATH, '').lstrip('/')
            folders = relative_path.split('/')
            parent_id = 'root'
            for folder in folders:
                query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
                results = drive_service.files().list(q=query, fields="files(id, name)").execute()
                files = results.get('files', [])
                if not files:
                    return []
                parent_id = files[0]['id']
            query = f"'{parent_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(name)").execute()
            return [file['name'] for file in results.get('files', [])]
        return retry_operation(list_f)
    except Exception as e:
        print(f"Erreur lors du listage des fichiers dans {category_path}: {str(e)}")
        return []

def upload_file(file_path, local_path):
    """Enregistre un fichier sur Google Drive"""
    try:
        def upload():
            relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
            folder_path = '/'.join(relative_path.split('/')[:-1])
            file_name = relative_path.split('/')[-1]
            create_folder(os.path.join(DATA_PATH, folder_path))
            parent_id = 'root'
            for folder in folder_path.split('/'):
                query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
                results = drive_service.files().list(q=query, fields="files(id)").execute()
                files = results.get('files', [])
                if not files:
                    return False
                parent_id = files[0]['id']
            file_metadata = {'name': file_name, 'parents': [parent_id]}
            media = MediaFileUpload(local_path)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            return True
        return retry_operation(upload)
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du fichier {file_path}: {str(e)}")
        return False

def download_file(file_path, local_path):
    """Télécharge un fichier depuis Google Drive"""
    try:
        def download():
            relative_path = file_path.replace(DATA_PATH, '').lstrip('/')
            folder_path = '/'.join(relative_path.split('/')[:-1])
            file_name = relative_path.split('/')[-1]
            parent_id = 'root'
            for folder in folder_path.split('/'):
                query = f"name='{folder}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
                results = drive_service.files().list(q=query, fields="files(id)").execute()
                files = results.get('files', [])
                if not files:
                    return False
                parent_id = files[0]['id']
            query = f"name='{file_name}' and '{parent_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            if not files:
                return False
            file_id = files[0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            return True
        return retry_operation(download)
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier {file_path}: {str(e)}")
        return False

def delete_device_folder(device_id):
    """Supprime le dossier d'un appareil sur Google Drive"""
    try:
        def delete():
            query = f"name='{device_id}' and mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            if not files:
                return False
            file_id = files[0]['id']
            drive_service.files().delete(fileId=file_id).execute()
            return True
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