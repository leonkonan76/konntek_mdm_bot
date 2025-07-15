import os
import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import logging

logger = logging.getLogger(__name__)

def generate_csv_report(logs, device_id, data_path):
    """Génère un rapport CSV pour les logs d'un appareil."""
    try:
        output_path = os.path.join(data_path, f"{device_id}_logs.csv")
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'User ID', 'Device ID', 'Category', 'Subcategory', 'Action', 'Timestamp'])
            for log in logs:
                writer.writerow(log)
        logger.info(f"Rapport CSV généré pour {device_id} à {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport CSV pour {device_id} : {e}")
        raise

def generate_pdf_report(logs, device_id, data_path):
    """Génère un rapport PDF pour les logs d'un appareil."""
    try:
        output_path = os.path.join(data_path, f"{device_id}_logs.pdf")
        c = canvas.Canvas(output_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, f"Rapport des logs pour l'appareil {device_id}")
        y = 700
        for log in logs:
            text = f"ID: {log[0]}, User: {log[1]}, Device: {log[2]}, Category: {log[3]}, Subcategory: {log[4]}, Action: {log[5]}, Time: {log[6]}"
            c.drawString(50, y, text)
            y -= 20
            if y < 50:
                c.showPage()
                y = 750
        c.save()
        logger.info(f"Rapport PDF généré pour {device_id} à {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport PDF pour {device_id} : {e}")
        raise
