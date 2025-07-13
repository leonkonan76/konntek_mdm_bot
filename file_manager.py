import os
import re
import shutil
from config import DATA_PATH

def validate_device_id(input_str):
    patterns = [
        r'^\d{15}$',  # IMEI
        r'^\w{5,20}$',  # SN
        r'^\+\d{11,15}$'  # Numéro international
    ]
    return any(re.match(p, input_str) for p in patterns)

def create_device_folder(device_id):
    base_path = os.path.join(DATA_PATH, device_id)
    os.makedirs(base_path, exist_ok=True)
    
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
    try:
        base_path = os.path.join(DATA_PATH, device_id)
        if os.path.exists(base_path):
            shutil.rmtree(base_path)
            return True
        return False
    except Exception as e:
        print(f"Erreur suppression: {e}")
        return False