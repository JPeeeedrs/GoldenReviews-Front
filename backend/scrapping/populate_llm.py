import json
import os
import sys
import sqlite3
import time
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_summary import gerar_resumo

# Mesma configuração de log
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

DB_PATH = r"c:\Desktop\goldenReviews\backend\cache.db"

def main():
    logging.info("🚀 Iniciando FASE 2: Geração de Resumos (Groq API) 🚀")
    
    # 1. Puxa todos os jogos do banco
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.execute("SELECT appid, data FROM game_cache WHERE status = 'completed'")
        rows = cursor.fetchall()

    if not rows:
        logging.info("Nenhum jogo encontrado no banco.")
        return

    jogos_atualizados = 0

    for appid, data_str in rows:
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue
            
        game_name = data.get("game", {}).get("name", f"App {appid}")
        summary = data.get("summary", {})
        texto_atual = summary.get("ai_text_summary", "")

        # 2. Verifica se o texto ainda está pendente ou tem aquele fallback padrão de antes
        precisa_processar = True

        if not precisa_processar:
            logging.info(f"[SKIP] {game_name} já possui resumo do Groq.")
            continue

        logging.info(f"✍️ A gerar resumo para: {game_name}...")

        # 3. Loop de insistência (Lida com o Rate Limit do Groq)
        sucesso = False
        tentativas = 0
        
        while not sucesso and tentativas < 5:
            try:
                # Chama a LLM passando os dados que já foram processados na Fase 1
                novo_resumo = gerar_resumo(data)
                
                # Atualiza o JSON
                data["summary"]["ai_text_summary"] = novo_resumo
                
                # Salva de volta no banco
                with sqlite3.connect(DB_PATH, timeout=10.0) as conn_update:
                    conn_update.execute("UPDATE game_cache SET data=?, updated_at=? WHERE appid=?",
                                        (json.dumps(data), time.time(), appid))
                
                logging.info(f"✅ Resumo de {game_name} guardado com sucesso!")
                sucesso = True
                jogos_atualizados += 1
                
                time.sleep(10) # Pausa curtinha entre jogos que deram certo
                
            except Exception as e:
                tentativas += 1
                logging.warning(f"⚠️ Groq Rate Limit ({e}). Pausando 60 segundos... (Tentativa {tentativas}/5)")
                time.sleep(60) # Cooldown de 1 minuto para restaurar a cota
                
        if not sucesso:
            logging.error(f"❌ Falha ao processar {game_name} após 5 tentativas. Pulando.")

    logging.info(f"🏁 FASE 2 CONCLUÍDA. Jogos atualizados com resumos: {jogos_atualizados} 🏁")

if __name__ == "__main__":
    main()