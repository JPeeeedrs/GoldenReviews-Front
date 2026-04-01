import requests
from collections import Counter
import spacy
import csv


def limpar_tokens(sent):
    tokens = []

    for token in sent:
        if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha:
            tokens.append(token.lemma_.lower())

    return tokens


# def gerar_frases(tokens):

#     frases = []

#     for i in range(len(tokens) - 2):
#         frase = tokens[i] + " " + tokens[i+1] + " " + tokens[i+2]
#         frases.append(frase)

#     return frases


def extrair_motivos(sent):
    
    motivos = []

   
    for token in sent:
        if token.pos_ == "NOUN" and token.is_alpha:
           
            adjs = [child.lemma_.lower() for child in token.children if child.pos_ == "ADJ" and child.is_alpha]
            if adjs:
                for adj in adjs:
                    motivos.append(f"{token.lemma_.lower()} {adj}")
            else:
                
                motivos.append(token.lemma_.lower())

    return motivos



def filtrar_motivos(motivos, total_reviews, limite_percentual=0.8):
   
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
        
        tokens = limpar_tokens(sent)
        tokens_total += tokens

        
        motivos = extrair_motivos(sent)
        motivos_total += motivos

    return tokens_total, motivos_total


arquivo = open("reviews.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(arquivo)

writer.writerow(["Review", "Recomendado", "Horas Jogadas"])

nlp = spacy.load("pt_core_news_sm")

idjogo = input("Digite o ID do jogo: ")

url = "https://store.steampowered.com/appreviews/" + idjogo

cursor = "*"
reviewsColetadas = 0
limiteReviews = 100


frasesPositivas = []
frasesNegativas = []

while reviewsColetadas < limiteReviews:

    params = {
        "json": 1,
        "num_per_page": 100,
        "language": "brazilian",
        "cursor": cursor
    }

    response = requests.get(url, params=params)
    data = response.json()

    reviews = data["reviews"]

    if len(reviews) == 0:
        break

    for review in reviews:

        texto = review["review"]

       
        tokens, motivos = processar_review(texto, nlp)

        writer.writerow([
            texto,
            review["voted_up"],
            review["author"]["playtime_forever"]
        ])

        if review["voted_up"]:
            frasesPositivas += motivos   
        else:
            frasesNegativas += motivos

    reviewsColetadas += len(reviews)

    print("Total de reviews coletadas:", reviewsColetadas)

    cursor = data["cursor"]



contadorFrasesPos = filtrar_motivos(frasesPositivas, reviewsColetadas)
contadorFrasesNeg = filtrar_motivos(frasesNegativas, reviewsColetadas)

print("\nMotivos mais comuns positivos:")
print(contadorFrasesPos.most_common(20))

print("\nMotivos mais comuns negativos:")
print(contadorFrasesNeg.most_common(20))

arquivo.close()