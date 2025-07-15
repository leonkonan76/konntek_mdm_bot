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

def generate_dashboard(db_name):
    """Génère un tableau de bord textuel des activités des utilisateurs"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    # Récupérer les utilisateurs uniques
    c.execute("SELECT DISTINCT user_id FROM user_access")
    users = c.fetchall()
    
    dashboard = ["📊 Tableau de bord des utilisateurs"]
    
    for user in users:
        user_id = user[0]
        c.execute(
            "SELECT action, timestamp FROM user_access WHERE user_id=? ORDER BY timestamp DESC LIMIT 5",
            (user_id,)
        )
        user_logs = c.fetchall()
        
        dashboard.append(f"\n👤 Utilisateur ID: {user_id}")
        for log in user_logs:
            action = log[0]
            timestamp = log[1]
            if action.startswith("DEVICE_ACCESS:"):
                device_id = action.split(":")[1]
                dashboard.append(f"  - {timestamp}: Accès au numéro {device_id}")
            elif action == "LOGIN_SUCCESS":
                dashboard.append(f"  - {timestamp}: Connexion réussie")
            elif action == "LOGIN_FAILED":
                dashboard.append(f"  - {timestamp}: Tentative de connexion échouée")
    
    conn.close()
    return "\n".join(dashboard) if dashboard else "ℹ️ Aucun log utilisateur disponible."
