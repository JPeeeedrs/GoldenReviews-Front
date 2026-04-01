import requests
from collections import Counter
import spacy
import csv

BLACKLIST = {
    "jogo", "game", "bom", "ruim", "muito", "muita", "coisa", "coisas",
    "pessoa", "pessoas", "vez", "vezes", "tempo", "ano", "anos",
    "ele", "ela", "isso", "aquele", "essa", "esse", "isto", "aquilo",
    "de", "da", "do", "em", "no", "na", "nos", "nas", "para", "com", "sem",
    "um", "uma", "uns", "umas", "os", "as", "por", "que", "como", "quando",
    "onde", "me", "minha", "meu", "tu", "nosso", "nós", "você", "voce",
    "eu", "não", "nao", "sim", "mas", "porque", "pq", "etc"
}

def limpar_tokens(sent):
    tokens = []
    for token in sent:
        if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha:
            tokens.append(token.lemma_.lower())
    return tokens

def extrair_motivos(sent):
    motivos = []
    for token in sent:
        if token.pos_ == "NOUN" and token.is_alpha:
            noun = token.lemma_.lower()
            if noun in BLACKLIST:
                continue
            adjs = [child.lemma_.lower() for child in token.children
                    if child.pos_ == "ADJ" and child.is_alpha and child.lemma_.lower() not in BLACKLIST]
            if adjs:
                for adj in adjs:
                    motivos.append(f"{noun} {adj}")
            else:
                motivos.append(noun)
    return motivos

def filtrar_motivos(motivos, total_reviews, limite_percentual=0.9):
    contador = Counter(motivos)
    resultado = Counter()
    for motivo, cnt in contador.items():
        if cnt / total_reviews <= limite_percentual:
            resultado[motivo] = cnt
    return resultado

def processar_review(texto, nlp):
    doc = nlp(texto)
    tokens_total = []
    motivos_total = []
    for sent in doc.sents:
        tokens_total += limpar_tokens(sent)
        motivos_total += extrair_motivos(sent)
    return tokens_total, motivos_total


nlp = spacy.load("pt_core_news_sm")
idjogo = input("Digite o ID do jogo: ")
url = "https://store.steampowered.com/appreviews/" + idjogo

cursor = "*"
reviewsColetadas = 0
limiteReviews = 500000
motivosPositivos = []
motivosNegativos = []
ids_vistos = set()

with open("reviews.csv", "w", newline="", encoding="utf-8") as arquivo:
    writer = csv.writer(arquivo)
    writer.writerow(["Review", "Recomendado", "Horas Jogadas"])

    while reviewsColetadas < limiteReviews:
        params = {
            "json": 1,
            "num_per_page": 10000,
            "language": "brazilian",
            "cursor": cursor,
            "filter": "recent"
        }

        response = requests.get(url, params=params)
        data = response.json()
        reviews = data.get("reviews", [])

        if not reviews:
            print("Sem mais reviews, encerrando.")
            break

        novas = 0
        for review in reviews:
            rid = review["recommendationid"]

            if rid in ids_vistos:
                continue
            ids_vistos.add(rid)

            texto = review["review"]
            tokens, motivos = processar_review(texto, nlp)

            writer.writerow([
                texto,
                review["voted_up"],
                review["author"]["playtime_forever"]
            ])

            motivos = list(set(motivos))
            if review["voted_up"]:
                motivosPositivos += motivos
            else:
                motivosNegativos += motivos

            novas += 1

        reviewsColetadas += novas
        print(f"Reviews únicas coletadas: {reviewsColetadas} (+{novas} novas)")

        novo_cursor = data.get("cursor", "")
        if not novo_cursor or novo_cursor == cursor:
            print("Cursor não avançou, encerrando.")
            break

        cursor = novo_cursor  

        if novas == 0:
            print("Nenhuma review nova nesta página, encerrando.")
            break

contadorPos = filtrar_motivos(motivosPositivos, reviewsColetadas)
contadorNeg = filtrar_motivos(motivosNegativos, reviewsColetadas)

print("\nMotivos mais comuns positivos:")
print(contadorPos.most_common(20))
print("\nMotivos mais comuns negativos:")
print(contadorNeg.most_common(20))