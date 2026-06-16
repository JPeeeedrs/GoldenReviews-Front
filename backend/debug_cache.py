import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "cache.db"

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT appid, status, data FROM game_cache WHERE data LIKE '%limite%' OR data LIKE '%requisiç%' LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        print(f"AppID: {row[0]}")
        print(f"Status: {row[1]}")
        print("-" * 40)
        print("Data (RAW):")
        print(row[2])
    else:
        print("Nenhum erro encontrado com essas palavras no banco.")