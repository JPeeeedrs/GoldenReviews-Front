import os
import json
from pathlib import Path
from google.genai import Client
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ Erro: A variável GEMINI_API_KEY não foi encontrada no ficheiro .env!")

client = Client(api_key=api_key)

MACRO_THEMES_BASE = [
    "🐛 Bugs e Crashes",
    "📉 Desempenho e FPS",
    "🎨 Gráficos e Visual",
    "🎮 Gameplay e Mecânicas",
    "📖 História e Narrativa",
    "🎵 Áudio e Som",
    "💰 Custo-Benefício",
    "🌐 Servidor e Online",
    "🌍 Tradução e Dublagem",
    "📦 DLCs e Conteúdo Adicional"
]

CATEGORY_TRASH = "🗑️ Lixo / Descartados"

TOPICS_JSON_PATH = Path("backend/steam_bertopic_model/topics.json")
OUTPUT_PATH = Path("grouped_topics_llm.json")

def classificar_com_ia(topics_dict):
    dados_para_ia = {}
    for tid, words in topics_dict.items():
        if str(tid) == "-1": continue
        
        if isinstance(words, list):

            if len(words) > 0 and isinstance(words[0], list):
                palavras = ", ".join([item[0] for item in words[:5]])
            else:
                palavras = ", ".join(words[:5])
        else:
            palavras = str(words)
            
        dados_para_ia[str(tid)] = palavras

    prompt = f"""
    És um analista de dados especialista em videojogos.
    Classifica os seguintes tópicos nos temas base: {", ".join(MACRO_THEMES_BASE)}.
    Se for necessário, cria novos temas com Emojis. Usa "{CATEGORY_TRASH}" para lixo.
    
    Devolve apenas JSON.
    
    Tópicos: {json.dumps(dados_para_ia, ensure_ascii=False)}
    """

    print("🧠 A enviar dados para a IA...")
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    
    return json.loads(response.text)

def main():
    if not TOPICS_JSON_PATH.exists():
        print(f"❌ Erro: Arquivo não encontrado em {TOPICS_JSON_PATH}")
        return

    print(f"📖 Lendo tópicos originais do BERTopic...")
    with open(TOPICS_JSON_PATH, "r", encoding="utf-8") as f:
        topics_data = json.load(f)

    if "topic_representations" in topics_data:
        topics_data = topics_data["topic_representations"]

    try:
        resultado_final = classificar_com_ia(topics_data)
        
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=4)

        print(f"✅ Sucesso Absoluto! JSON salvo em {OUTPUT_PATH}")
        
        temas_gerados = list(resultado_final.keys())
        novos_temas = [t for t in temas_gerados if t not in MACRO_THEMES_BASE and t != CATEGORY_TRASH]
        if novos_temas:
            print(f"✨ A IA descobriu {len(novos_temas)} NOVOS temas que não estavam na sua lista base:")
            for nt in novos_temas:
                print(f"   - {nt}")
                
    except Exception as e:
        print(f"❌ Erro na comunicação com a API: {e}")

if __name__ == "__main__":
    main()