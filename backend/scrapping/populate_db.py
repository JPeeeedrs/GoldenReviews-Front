import json
import sqlite3
import time
import os
import logging
import gc
import torch

from app import fetch_reviews, fetch_game_details, PIPELINE, DB_PATH

# =========================================================================
# CONFIGURAÇÃO DO SISTEMA DE LOGS
# =========================================================================
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
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
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
    
    # 1. Verifica se já está no banco
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.execute("SELECT status FROM game_cache WHERE appid = ?", (appid,))
        row = cursor.fetchone()
        if row and row[0] == "completed":
            logging.info(f"[SKIP] Jogo {game_name} ({appid}) já está na base de dados!")
            return True

    logging.info(f"\n[{game_name}] A iniciar extração de até {MAX_REVIEWS} reviews...")
    
    try:
        # 2. Busca na Steam
        reviews = fetch_reviews(appid, MAX_REVIEWS, IDIOMA)
        game_details = fetch_game_details(appid)
        
        if not reviews:
            logging.warning(f"[{game_name}] Ignorado: Nenhuma review em PT-BR encontrada.")
            return False

        if len(reviews) < 100:
            logging.warning(f"[{game_name}] Ignorado: Apenas {len(reviews)} reviews recolhidas.")
            return False
            
        logging.info(f"[{game_name}] Recolhidas {len(reviews)} reviews. A processar BERTopic...")
        
        # 3. Processa no Pipeline (BERTopic)
        analysis_result = PIPELINE.process_reviews(reviews, game_details)
        analysis_result["game"] = {**analysis_result.get("game", {}), **game_details}

        # 4. Matemática Exata das Frases (Nova Lógica)
        topicos_positivos = analysis_result.get("topics", {}).get("positive", [])
        topicos_negativos = analysis_result.get("topics", {}).get("negative", [])

        frases_positivas = sum(t.get("mentions", 0) for t in topicos_positivos)
        frases_negativas = sum(t.get("mentions", 0) for t in topicos_negativos)
        total_frases = frases_positivas + frases_negativas

        pct_positiva = round((frases_positivas / total_frases) * 100) if total_frases > 0 else 0
        pct_negativa = round((frases_negativas / total_frases) * 100) if total_frases > 0 else 0

        total_reviews_baixadas = len(reviews)
        avg_hours = sum(r.get("hours", 0) for r in reviews) / total_reviews_baixadas if total_reviews_baixadas > 0 else 0
        
        if "summary" not in analysis_result:
            analysis_result["summary"] = {}
            
        analysis_result["summary"].update({
            "reviews_analyzed": total_reviews_baixadas,
            "avg_hours": avg_hours,
            "sentences_positive_count": frases_positivas,
            "sentences_negative_count": frases_negativas,
            "sentences_positive_percentage": pct_positiva,
            "sentences_negative_percentage": pct_negativa,
            "total_extracted_sentences": total_frases,
            "ai_text_summary": "Pendente de Processamento (Fase 2)" # Marcação provisória
        })

        # 5. Guarda o progresso no Banco IMEDIATAMENTE (Sem chamar o Groq)
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO game_cache (appid, status, data, updated_at) VALUES (?, ?, ?, ?)",
                (appid, 'completed', json.dumps(analysis_result), time.time())
            )
            
        logging.info(f"✅ [{game_name}] Análise BERT concluída e guardada!")
        return True

    except Exception as e:
        logging.error(f"❌ Erro crítico ao processar {game_name} ({appid}): {e}")
        return False

def main():
    logging.info("🚀 A iniciar FASE 1: Extração e BERTopic 🚀")
    init_db()

    if not os.path.exists(ARQUIVO_JSON):
        logging.error(f"Erro fatal: Ficheiro {ARQUIVO_JSON} não encontrado!")
        return

    with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
        jogos_lista = json.load(f)

    jogos_para_processar = jogos_lista[:LIMITE_JOGOS]
    sucessos = 0

    for i, jogo in enumerate(jogos_para_processar):
        appid = jogo.get("steam_appid_ref") or jogo.get("appid")
        nome = jogo.get("game", {}).get("name", "Jogo Desconhecido") if "game" in jogo else "Jogo Desconhecido"
        
        if not appid:
            continue
            
        logging.info(f"--- Progresso: {i+1}/{len(jogos_para_processar)} | Jogo: {nome} ---")
        if processar_jogo(appid, nome):
            sucessos += 1
            
        time.sleep(2) # Pausa mínima só para Steam respirar

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    logging.info(f"🏁 FASE 1 CONCLUÍDA. Sucessos: {sucessos} 🏁")

if __name__ == "__main__":
    main()