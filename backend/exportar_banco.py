import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"
OUTPUT_FILE = BASE_DIR / "todos_os_jogos_do_banco.json"

def exportar_jogos():
    print("Conectando ao banco de dados para exportação...")
    
    lista_de_jogos = []
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT appid, data FROM game_cache WHERE status = 'completed'")
            rows = cursor.fetchall()
            
            for appid, data_str in rows:
                try:
                    game_data = json.loads(data_str)
                    
                    game_data["steam_appid_ref"] = appid 
                    
                    lista_de_jogos.append(game_data)
                    
                except json.JSONDecodeError:
                    print(f"[!] Erro ao ler os dados do jogo {appid}. Pulando...")
                    
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(lista_de_jogos, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Sucesso! {len(lista_de_jogos)} jogos foram exportados.")
        print(f"📂 Arquivo salvo em: {OUTPUT_FILE.absolute()}")
        
    except Exception as e:
        print(f"❌ Ocorreu um erro ao acessar o banco: {e}")

if __name__ == "__main__":
    exportar_jogos()