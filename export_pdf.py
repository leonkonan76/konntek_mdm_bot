import sqlite3
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

def export_logs_pdf(target_id: str, db_path="konntek.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT action, file, timestamp FROM logs WHERE target_id = ?", (target_id,))
    rows = cursor.fetchall()
    output_path = f"data/{target_id}/analyse/logs_export.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Rapport d'activite - {target_id}")
    c.drawString(50, 755, f"Export : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, 740, "--------------------------")
    y = 720
    for action, file, timestamp in rows:
        line = f"[{timestamp}] {action.upper()} - {file}"
        c.drawString(50, y, line)
        y -= 15
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = 770
    c.save()
    return output_path