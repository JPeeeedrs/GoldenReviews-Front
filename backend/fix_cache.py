import sqlite3
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"

def fix_failed_summaries():
    print("Iniciando correção estrutural e focada no erro 429...")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT appid, data, status FROM game_cache")
        rows = cursor.fetchall()
        
        updated_count = 0
        
        for appid, data_str, status in rows:
            if not data_str:
                continue
                
            try:
                data = json.loads(data_str)
                summary = data.get("summary", {})
                ai_text_summary = summary.get("ai_text_summary", "")
                
                texto_analise = ""
                
                # 1. Isola o texto onde a IA pode ter salvo a mensagem de limite excedido
                if isinstance(ai_text_summary, dict):
                    texto_analise = str(ai_text_summary.get("resumo", "")).lower()
                elif isinstance(ai_text_summary, str):
                    texto_analise = ai_text_summary.lower()
                
                erro_raiz = str(data.get("error", "")).lower()
                texto_analise += " " + erro_raiz
                
                # 2. Termos exatos que a API do Google/OpenAI retornam quando a cota estoura
                erros_api = ["429", "exhausted", "quota", "too many requests", "resource has been"]
                
                precisa_corrigir = any(kw in texto_analise for kw in erros_api) or status == 'error'
                
                if precisa_corrigir:
                    print(f"-> Corrigindo AppID {appid} (Erro de API detectado)...")
                    
                    score_final = summary.get("overall_score", 0.0)
                    total_revs = summary.get("reviews_analyzed", 0)
                    pct_pos = summary.get("positive_percentage", 0)
                    
                    novo_texto = (
                        f"Análise baseada em {total_revs} reviews recentes da Steam. "
                        f"O jogo apresenta um índice de aprovação de {pct_pos}% pelos usuários, "
                        f"com uma nota de sentimento calculada em {score_final}/5.0 baseada nos tópicos identificados."
                    )
                    
                    # 3. Salva no formato de objeto, igual aos jogos que deram certo
                    if "summary" not in data:
                        data["summary"] = {}
                        
                    data["summary"]["ai_text_summary"] = {
                        "nota_ia": score_final,
                        "resumo": novo_texto
                    }
                    
                    if "error" in data:
                        del data["error"]
                    
                    cursor.execute(
                        "UPDATE game_cache SET data = ?, status = 'completed', updated_at = ? WHERE appid = ?",
                        (json.dumps(data), time.time(), appid)
                    )
                    updated_count += 1
                    
            except Exception as e:
                print(f"[!] Erro inesperado ao processar AppID {appid}: {e}")
        
        conn.commit()
        
    print(f"\nFinalizado! {updated_count} jogos que estavam travados foram restaurados com o Plano B.")

if __name__ == "__main__":
    fix_failed_summaries()