import sqlite3
import pandas as pd

def export_logs_csv(target_id: str, db_path="konntek.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM logs WHERE target_id = ?", conn, params=(target_id,))
    output_path = f"data/{target_id}/analyse/logs_export.csv"
    df.to_csv(output_path, index=False)
    return output_path