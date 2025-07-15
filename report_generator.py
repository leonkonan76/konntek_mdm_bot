# report_generator.py
import csv
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from config import DB_NAME

def generate_csv(db_name, device_id):
    """Génère un rapport CSV des logs"""
    filename = f"{device_id}_logs.csv"
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE device_id=?", (device_id,))
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Device ID', 'Action', 'File Path', 'Timestamp'])
        writer.writerows(c.fetchall())
    
    conn.close()
    return filename

def generate_pdf(db_name, device_id):
    """Génère un rapport PDF des logs"""
    filename = f"{device_id}_report.pdf"
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE device_id=?", (device_id,))
    logs = c.fetchall()
    conn.close()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Rapport d'activité pour {device_id}", styles['Title'])]
    
    for log in logs:
        story.append(Paragraph(
            f"{log[4]}: {log[2]} - {log[3] or 'Aucun fichier'}", 
            styles['BodyText']
        ))
    
    doc.build(story)
    return filename
