"""
Script 1: train_offline.py (Treinamento Base)
Objetivo: Resolver o Cold Start utilizando um dataset estático do Kaggle.
"""

import pandas as pd
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
import nltk
import ssl
import certifi

# Bypass para download nltk se houver problemas de SSL
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt')

def main():
    print("1. Carregando dataset estático com reviews da Steam...")
    # Substitua pelo caminho do seu arquivo Kaggle
    df = pd.read_csv("steam_reviews.csv") 

    # Considerando que existe uma coluna 'review'
    reviews = df['review'].dropna().tolist()

    # Extraindo uma amostra grande de textos (ex: 20000 para não estourar RAM local)
    amostra_reviews = reviews[:20000]

    print("2. Quebrando os textos em frases...")
    sentences = []
    for review in amostra_reviews:
        # Fatiamento em frases
        frases = nltk.sent_tokenize(review, language='portuguese')
        sentences.extend([f.strip() for f in frases if len(f.strip()) > 30])
    
    print(f"Total de frases extraídas: {len(sentences)}")

    print("3. Carregando MiniLM para gerar os embeddings...")
    embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    print("Gerando embeddings (isso pode demorar)....")
    embeddings = embedding_model.encode(sentences, show_progress_bar=True)

    print("4. Treinando o BERTopic do zero...")
    topic_model = BERTopic(
        embedding_model=embedding_model,
        language="multilingual",
        verbose=True
    )
    
    # Treina o modelo nos dados
    topic_model.fit(sentences, embeddings)

    print("5. Salvando o modelo treinado em disco...")
    topic_model.save("steam_bertopic_model", serialization="safetensors")
    print("Pipeline de Treinamento Offline concluído com sucesso!")

if __name__ == "__main__":
     main()
    
