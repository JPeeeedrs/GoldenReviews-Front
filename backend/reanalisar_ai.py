import sqlite3
import json
import time
from pathlib import Path
from llm_summary import gerar_resumo

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"

def reanalisar_jogos_com_erro():
    print("Buscando jogos com o aviso de limite de requisições...")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT appid, data FROM game_cache WHERE data LIKE '%temporariamente indisponível%'")
        rows = cursor.fetchall()

        if not rows:
            print("Nenhum jogo com essa mensagem foi encontrado no banco.")
            return

        print(f"Encontrados {len(rows)} jogos. Iniciando re-análise via Groq/LLM...")
        
        sucessos = 0
        for appid, data_str in rows:
            try:
                data = json.loads(data_str)
                print(f"-> Re-analisando AppID {appid}...")
                
                resultado_ia = gerar_resumo(data)
                
                data["summary"]["ai_text_summary"] = resultado_ia
                
                cursor.execute(
                    "UPDATE game_cache SET data = ?, updated_at = ? WHERE appid = ?",
                    (json.dumps(data), time.time(), appid)
                )
                sucessos += 1
                print(f"   [OK] AppID {appid} re-analisado e atualizado!")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"   [ERRO] Falha ao tentar re-analisar AppID {appid}: {e}")
        
        conn.commit()
        print(f"\nFinalizado! {sucessos} jogos foram curados e atualizados.")

if __name__ == "__main__":
    reanalisar_jogos_com_erro()