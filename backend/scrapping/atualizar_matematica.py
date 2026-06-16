import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

DB_PATH = r"c:\Desktop\goldenReviews\backend\cache.db"

def main():
    logging.info("🚀 Iniciando migração da matemática das frases no Banco de Dados...")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT appid, data, status FROM game_cache WHERE status = 'completed'")
        rows = cursor.fetchall()
        
        if not rows:
            logging.info("Nenhum jogo 'completed' encontrado no banco para atualizar.")
            return

        jogos_atualizados = 0

        for appid, data_str, status in rows:
            try:
                data = json.loads(data_str)
            except Exception as e:
                logging.error(f"Erro ao ler JSON do appid {appid}: {e}")
                continue
                
            game_name = data.get("game", {}).get("name", f"App {appid}")
            summary = data.get("summary", {})
            
            # 1. Puxa as frases já guardadas pela IA nas execuções passadas
            topicos_positivos = data.get("topics", {}).get("positive", [])
            topicos_negativos = data.get("topics", {}).get("negative", [])

            # 2. Faz a nova matemática
            frases_positivas = sum(t.get("mentions", 0) for t in topicos_positivos)
            frases_negativas = sum(t.get("mentions", 0) for t in topicos_negativos)
            total_frases = frases_positivas + frases_negativas

            pct_positiva = round((frases_positivas / total_frases) * 100) if total_frases > 0 else 0
            pct_negativa = round((frases_negativas / total_frases) * 100) if total_frases > 0 else 0
            
            # 3. Atualiza o dicionário summary com as novas chaves
            data["summary"].update({
                "sentences_positive_count": frases_positivas,
                "sentences_negative_count": frases_negativas,
                "sentences_positive_percentage": pct_positiva,
                "sentences_negative_percentage": pct_negativa,
                "total_extracted_sentences": total_frases
            })
            
            # 4. Salva de volta no banco
            conn.execute("UPDATE game_cache SET data=? WHERE appid=?", (json.dumps(data), appid))
            jogos_atualizados += 1
            
        logging.info(f"✅ Migração concluída! {jogos_atualizados} jogos foram atualizados com a nova matemática das frases.")

if __name__ == "__main__":
    main()