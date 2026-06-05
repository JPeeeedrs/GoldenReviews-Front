"""
Script 1: train_offline.py (Treinamento Base)
Objetivo: Resolver o Cold Start utilizando um dataset estático do Kaggle.
"""

import pandas as pd
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords
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
nltk.download('stopwords')

# 1. Configurando Stop Words (Removendo lixo e nomes genéricos de jogos)
stop_words_pt = stopwords.words('portuguese')
custom_stop_words = stop_words_pt + [
    'jogo', 'jogar', 'game', 'steam', 'pra', 'pro', 'the', 'witcher',
    'batman', 'resident', 'evil', 'jogabilidade', 'horas', 'td', 'tr', 'h1',
    'list', 'url', 'kkkk', 'kkkkk', 'cities', 'skylines', 'souls', 'arkham',
    'capcom', 'revelations'
]
vectorizer_model = CountVectorizer(stop_words=custom_stop_words)

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
        sentences.extend([f.strip() for f in frases if len(f.strip()) > 10])
    
    print(f"Total de frases extraídas: {len(sentences)}")

    print("3. Carregando MiniLM para gerar os embeddings...")
    embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    print("Gerando embeddings (isso pode demorar)....")
    embeddings = embedding_model.encode(sentences, show_progress_bar=True)

    print("4. Treinando o BERTopic parametrizado...")
    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        language="multilingual",
        nr_topics="auto",
        min_topic_size=15,
        verbose=True
    )
    
    topics, probs = topic_model.fit_transform(sentences, embeddings)

    print("5. Aplicando redução moderada de outliers (Threshold: 0.85)...")
    # Resgata apenas os outliers que tenham 85% ou mais de similaridade com um tópico existente
    new_topics = topic_model.reduce_outliers(
        sentences,
        topics,
        strategy="embeddings",
        threshold=0.85
    )

    # Atualiza o modelo com os outliers resgatados
    topic_model.update_topics(sentences, topics=new_topics)

    print("6. Salvando o modelo refinado em disco...")
    topic_model.save("steam_bertopic_model", serialization="safetensors")
    print("Pipeline de Treinamento Offline concluído com sucesso!")

if __name__ == "__main__":
     main()
    
