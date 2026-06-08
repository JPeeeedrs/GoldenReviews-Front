# Treinamento Offline do BERTopic para Análise de Tópicos em Reviews da Steam

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


# Expanção da lista de stop words para incluir termos comuns em reviews de jogos, gírias e lixo HTML. Organizado em categorias para facilitar manutenção futura.

stop_words_pt = stopwords.words('portuguese')

termos_plataforma_metalinguagem = [
    'jogo', 'jogar', 'game', 'steam', 'horas', 'pc', 'computador', 
    'recomendo', 'recomendar', 'joguei', 'jogando', 'zerar', 'zerei', 
    'review', 'analise', 'análise', 'mouse', 'teclado'
]

internet_e_girias = [
    'pra', 'pro', 'q', 'vc', 'tbm', 'tb', 'pq', 'mt', 'mto', 'ta', 'tá', 
    'né', 'ne', 'eh', 'nd', 'oq', 'kkk', 'kkkk', 'kkkkk', 'ksksks', 'rs', 'poha'
]

lixo_html_api = [
    'td', 'tr', 'h1', 'list', 'url', 'br', 'div', 'span', 'href', 
    'http', 'https', 'img', 'b', 'i'
]


nomes_franquias_e_empresas = [
    
    'ubisoft', 'ea', 'rockstar', 'bethesda', 'valve', 'capcom', 'fromsoftware', 
    'sony', 'microsoft', 'cdpr', 'projekt', 'red', 'square', 'enix',
    'the', 'witcher', 'batman', 'resident', 'evil', 'cities', 'skylines', 
    'souls', 'arkham', 'revelations', 'gta', 'cyberpunk', 'skyrim', 'fallout', 
    'assassins', 'creed', 'farcry', 'fifa', 'cod', 'call', 'duty', 'battlefield', 
    'csgo', 'cs', 'dota', 'pubg', 'minecraft', 'terraria', 'stardew', 'valley',
    'halo', 'bioshock', 'persona', 'zelda', 'mario'
]

custom_stop_words = (
    stop_words_pt + 
    termos_plataforma_metalinguagem + 
    internet_e_girias + 
    lixo_html_api + 
    nomes_franquias_e_empresas
)

vectorizer_model = CountVectorizer(stop_words=custom_stop_words)

def main():
    print("1. Carregando dataset estático com reviews da Steam...")
    
    df = pd.read_csv("steam_reviews.csv") 

    
    reviews = df['review'].dropna().tolist()

    # Aumentando a amostra de 20000 para 30.000 reviews para capturar mais diversidade de tópicos, mantendo um tamanho gerenciável para o treinamento offline.
    amostra_reviews = reviews[:30000]

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

# TODO: Analisar possível mudança de modelo de embedding, definir um nr_topics fixo razoável e verificar os tópicos já gerados para ajustar o min_topic_size.
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
    
