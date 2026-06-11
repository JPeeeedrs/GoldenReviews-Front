
# Este script é uma ferramenta de depuração para extrair dados do cache do jogo a partir de um banco de dados SQLite. Ele solicita ao usuário o AppID do jogo, consulta o banco de dados para encontrar os dados correspondentes e salva esses dados em um arquivo JSON para análise posterior.

import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"

def extrair_cache():
    # 🌟 O CONSERTO: Agora o terminal vai te perguntar qual o ID!
    appid = input("Digite o AppID do jogo que quer debugar (ex: 2356550 para Overwatch): ").strip()
    
    if not appid:
        print("❌ Nenhum ID digitado. Cancelando...")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Ele busca exatamente o ID que você digitou
            cursor = conn.execute("SELECT data FROM game_cache WHERE appid = ?", (appid,))
            row = cursor.fetchone()
            
            if row:
                dados = json.loads(row[0])
                
                # Salva o arquivo com o nome dinâmico, ex: debug_2356550.json
                output_path = BASE_DIR / f"debug_{appid}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(dados, f, indent=4, ensure_ascii=False)
                    
                print(f"✅ Sucesso! O arquivo foi salvo em: {output_path}")
            else:
                print(f"❌ Jogo {appid} não encontrado no banco de dados. Você já pesquisou ele no navegador hoje?")
    except Exception as e:
        print(f"Erro ao acessar o banco de dados: {e}")

if __name__ == "__main__":
    extrair_cache()