import os
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def obter_chaves_disponiveis():
    chaves = []
    for i in range(1, 6):
        key = os.getenv(f"GROQ_API_KEY_{i}")
        if key and key.strip():
            chaves.append(key)
    
    if not chaves:
        default_key = os.getenv("GROQ_API_KEY")
        if default_key:
            chaves.append(default_key)
            
    return chaves

def gerar_resumo(analysis_result: dict) -> dict:
    api_keys = obter_chaves_disponiveis()
    
    if not api_keys:
        raise Exception("Sem chave de API configurada! Acionando Plano B automático...")

    game_name = analysis_result.get("game", {}).get("name", "Jogo")
    
    # 1. Puxamos a matemática exata das frases!
    summary_data = analysis_result.get("summary", {})
    pct_positiva = summary_data.get("sentences_positive_percentage", 0)
    pct_negativa = summary_data.get("sentences_negative_percentage", 0)

    # 2. Calculamos a nota matematicamente (Regra de 3 direta: 100% = 5.0)
    # Ex: 50% positivas = 2.5 de nota. 80% positivas = 4.0 de nota.
    nota_calculada = round((pct_positiva / 100) * 5.0, 1)

    pos_topics = [t["topic"] for t in analysis_result.get("topics", {}).get("positive", [])[:3]]
    neg_topics = [t["topic"] for t in analysis_result.get("topics", {}).get("negative", [])[:3]]
    
    str_positivos = ", ".join(pos_topics) if pos_topics else "Nenhum ponto positivo forte detectado."
    str_negativos = ", ".join(neg_topics) if neg_topics else "Nenhum problema grave relatado."

    # 3. Prompt estrito: Amarrando a IA à NOSSA matemática
    prompt = f"""
Você é um crítico de jogos rigoroso, direto e imparcial.

DADOS REAIS DO JOGO:
- Nome: {game_name}
- Frases Positivas: {pct_positiva}%
- Frases Negativas: {pct_negativa}%
- Elogios principais: {str_positivos}
- Reclamações principais: {str_negativos}

A matemática da nossa análise já definiu que a NOTA JUSTA deste jogo é {nota_calculada} de 5.0.

SUA TAREFA:
1. Escreva um RESUMO em um único parágrafo (máximo 4 linhas) justificando essa nota com base nos dados. 
2. Seja realista: se a nota for baixa ou mediana, não tente suavizar os problemas. Destaque as reclamações principais sem dó.
3. Não use jargões robóticos, escreva como um humano avaliando o jogo.
4. Devolva a resposta EXATAMENTE neste formato:

NOTA: [Sua nota aqui]
RESUMO: [Seu texto aqui]
"""

    for index, api_key in enumerate(api_keys):
        num_tentativa = index + 1
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            
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
            erro_msg = str(e).lower()
            if "429" in erro_msg or "rate limit" in erro_msg or "too many requests" in erro_msg:
                logging.warning(f"[Groq] Chave {num_tentativa} atingiu o limite. Rotacionando...")
                continue
            else:
                logging.error(f"[Groq] Erro com a chave {num_tentativa}: {e}")
                continue

    raise Exception("Todas as chaves falharam ou estão esgotadas. Acionando Plano B automático...")
