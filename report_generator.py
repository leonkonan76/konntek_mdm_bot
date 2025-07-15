import sqlite3
import csv
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_csv(db_name, device_id):
    """Génère un rapport CSV pour un appareil spécifique"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    c.execute("SELECT * FROM logs WHERE device_id = ?", (device_id,))
    logs = c.fetchall()
    
    filename = f"logs_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'User ID', 'Device ID', 'Action', 'File Path', 'Timestamp'])
        for log in logs:
            writer.writerow(log)
    
    conn.close()
    return filename

def generate_pdf(db_name, device_id):
    """Génère un rapport PDF pour un appareil spécifique"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    c.execute("SELECT * FROM logs WHERE device_id = ?", (device_id,))
    logs = c.fetchall()
    
    filename = f"report_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, f"Rapport pour l'appareil {device_id}")
    y = 700
    for log in logs:
        c.drawString(100, y, f"{log[0]} | {log[1]} | {log[2]} | {log[3]} | {log[4]} | {log[5]}")
        y -= 20
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    
    conn.close()
    return filename

def generate_dashboard(db_name):
    """Génère un tableau de bord textuel avec des statistiques"""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(DISTINCT device_id) FROM devices")
    total_devices = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM logs")
    total_logs = c.fetchone()[0]
    
    c.execute("SELECT device_id, COUNT(*) as count FROM logs GROUP BY device_id ORDER BY count DESC LIMIT 5")
    top_devices = c.fetchall()
    
    dashboard = f"📊 Tableau de bord\n\n"
    dashboard += f"Nombre total d'appareils: {total_devices}\n"
    dashboard += f"Nombre total d'actions: {total_logs}\n\n"
    dashboard += "Top 5 appareils par activité:\n"
    for device, count in top_devices:
        dashboard += f"- {device}: {count} actions\n"
    
    conn.close()
    return dashboard
