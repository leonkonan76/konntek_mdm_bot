import csv
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from config import DB_NAME

def generate_csv(device_id):
    filename = f"{device_id}_logs.csv"
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE device_id=?", (device_id,))
    logs = c.fetchall()
    conn.close()
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Device ID', 'Action', 'File Path', 'Timestamp'])
        writer.writerows(logs)
    
    return filename

def generate_pdf(device_id):
    filename = f"{device_id}_report.pdf"
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE device_id=?", (device_id,))
    logs = c.fetchall()
    conn.close()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Rapport d'activité pour {device_id}", styles['Title'])]
    
    for log in logs:
        story.append(Paragraph(f"{log[4]}: {log[2]} - {log[3]}", styles['BodyText']))
    
    doc.build(story)
    return filename