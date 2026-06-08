
import os
from urllib import response
from openai import OpenAI
from dotenv import load_dotenv
from pyparsing import line

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("❌ Erro: A variável GROQ_API_KEY não foi encontrada no ficheiro .env!")


client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)
# client = Client(api_key=api_key)

def gerar_resumo(analysis_result: dict) -> str:

    game_name = analysis_result.get("game", {}).get("name", "Jogo")

    pos_topics = [t["topic"] for t in analysis_result.get("topics", {}).get("positive", [])[:3]]
    neg_topics = [t["topic"] for t in analysis_result.get("topics", {}).get("negative", [])[:3]]
    
    str_positivos = ", ".join(pos_topics) if pos_topics else "Nenhum ponto positivo forte detectado."
    str_negativos = ", ".join(neg_topics) if neg_topics else "Nenhum problema grave relatado."

    prompt = f"""
    Você é um assistente especialista em analisar avaliações de jogos na Steam.
    Com base nos dados abaixo, responda exatamente neste formato, sem texto adicional:

    NOTA: [número de 0.0 a 5.0 com uma casa decimal]
    RESUMO: [texto corrido de no máximo 3 frases, estilo Mercado Livre, dizendo se vale a pena, o que elogiam, o que criticam e o veredito final]

    Dados do Jogo: {game_name}
    Principais Elogios: {str_positivos}
    Principais Críticas: {str_negativos}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        content = response.choices[0].message.content.strip()
        nota = 0.0
        resumo = ""
    
        for line in content.splitlines():
            if line.startswith("NOTA:"):
                try:
                    nota = float(line.replace("NOTA:", "").strip())
                except ValueError:
                    nota = 0.0
            elif line.startswith("RESUMO:"):
                resumo = line.replace("RESUMO:", "").strip()

        return {"nota_ia": nota, "resumo": resumo}
        
    
    except Exception as e:
        print(f"Erro ao gerar resumo via LLM: {e}")
        return {"nota_ia": 0.0, "resumo": "Não foi possível gerar o resumo no momento."}