import json
import sqlite3
import time
import os
import logging
import gc
import torch

from app import fetch_reviews, fetch_game_details, PIPELINE, DB_PATH
from llm_summary import gerar_resumo

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()                             
    ]
)

ARQUIVO_JSON = "todos_os_jogos_do_banco.json"  
MAX_REVIEWS = 5000
IDIOMA = "brazilian"
LIMITE_JOGOS = 1000 

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_cache (
                appid TEXT PRIMARY KEY,
                status TEXT,
                data TEXT,
                updated_at REAL
            )
            """
        )

def processar_jogo(appid: str, game_name: str):
    appid = str(appid)
    
    # 1. Verifica se o jogo já foi processado com sucesso antes
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT status FROM game_cache WHERE appid = ?", (appid,))
        row = cursor.fetchone()
        if row and row[0] == "completed":
            logging.info(f"[SKIP] Jogo {game_name} ({appid}) já está na base de dados!")
            return True

    logging.info(f"\n[{game_name}] A iniciar extração de até {MAX_REVIEWS} reviews...")
    
    try:
        # 2. Procura as reviews na API da Steam (Usa a correção do purchase_type='all')
        reviews = fetch_reviews(appid, MAX_REVIEWS, IDIOMA)
        game_details = fetch_game_details(appid)
        
        if not reviews:
            logging.warning(f"[{game_name}] Ignorado: Nenhuma review em PT-BR encontrada.")
            return False

        # 3. Regra de Segurança: Filtro anti-gargalo (Ex: Caso do PUBG com poucas reviews)
        if len(reviews) < 100:
            logging.warning(f"[{game_name}] Ignorado: Apenas {len(reviews)} reviews recolhidas. Quantidade insuficiente para análise!")
            return False
            
        logging.info(f"[{game_name}] Recolhidas {len(reviews)} reviews. A processar Inteligência Artificial (BERTopic)...")
        
        # 4. Processa no seu Pipeline Local otimizado para GPU
        analysis_result = PIPELINE.process_reviews(reviews, game_details)
        analysis_result["game"] = {**analysis_result.get("game", {}), **game_details}

        # 5. Cálculos estatísticos para o Frontend
        total = len(reviews)
        pos_count = sum(1 for r in reviews if r.get("recommended"))
        neg_count = total - pos_count
        pos_pct = round((pos_count / total) * 100) if total > 0 else 0
        neg_pct = round((neg_count / total) * 100) if total > 0 else 0
        avg_hours = sum(r.get("hours", 0) for r in reviews) / total if total > 0 else 0
        
        if "summary" not in analysis_result:
            analysis_result["summary"] = {}
            
        analysis_result["summary"].update({
            "reviews_analyzed": total,
            "positive_count": pos_count,
            "positive_percentage": pos_pct,
            "negative_count": neg_count,
            "negative_percentage": neg_pct,
            "avg_hours": avg_hours
        })

        # 6. Gera o Resumo utilizando a API ultra-rápida do GROQ (Llama 3)
        logging.info(f"[{game_name}] A gerar Resumo de texto com a API do Groq...")
        texto_resumo = gerar_resumo(analysis_result)
        analysis_result["summary"]["ai_text_summary"] = texto_resumo

        # 7. Guarda o progresso de forma cirúrgica na Base de Dados
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO game_cache (appid, status, data, updated_at) VALUES (?, ?, ?, ?)",
                (appid, 'completed', json.dumps(analysis_result), time.time())
            )
            
        logging.info(f"✅ [{game_name}] Concluído com sucesso e guardado!")
        return True

    except Exception as e:
        logging.error(f"❌ Erro crítico ao processar {game_name} ({appid}): {e}")
        return False

def main():
    logging.info("🚀 A iniciar Script de População em Massa Golden Reviews (Versão Groq + Logs) 🚀")
    init_db()

    if not os.path.exists(ARQUIVO_JSON):
        logging.error(f"Erro fatal: Ficheiro {ARQUIVO_JSON} não encontrado na pasta!")
        return

    with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
        jogos_lista = json.load(f)

    jogos_para_processar = jogos_lista[:LIMITE_JOGOS]

    logging.info(f"Encontrados {len(jogos_lista)} jogos no JSON. Alvo: Processar {len(jogos_para_processar)} jogos.")
    
    sucessos = 0
    falhas = 0

    for i, jogo in enumerate(jogos_para_processar):

        appid = jogo.get("steam_appid_ref") or jogo.get("appid")
        
        nome = "Jogo Desconhecido"
        if "game" in jogo and "name" in jogo["game"]:
            nome = jogo["game"]["name"]
        
        if not appid:
            continue
            
        logging.info(f"\n--- Progresso: {i+1}/{len(jogos_para_processar)} ---")
        sucesso = processar_jogo(appid, nome)
        
        if sucesso:
            sucessos += 1
        else:
            falhas += 1
            
        time.sleep(10)

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    logging.info("\n" + "="*40)
    logging.info("🏁 RELATÓRIO FINAL DO SCRAPER 🏁")
    logging.info(f"Total Processado: {len(jogos_para_processar)}")
    logging.info(f"Sucessos Gravados: {sucessos}")
    logging.info(f"Falhas/Ignorados: {falhas}")
    logging.info("="*40)

if __name__ == "__main__":
    main()