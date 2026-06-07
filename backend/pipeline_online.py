"""
Script 2: pipeline_online.py (Inferência e ABSA)
Objetivo: Script central para o backend FastAPI (ou Flask) que recebe reviews novas 
e aplica ABSA (Aspect-Based Sentiment Analysis) usando BERTopic em tempo real.
"""

from __future__ import annotations
import nltk
import ssl
import pandas as pd
from typing import Any, Dict, List
import time
import torch
import torch.nn.functional as F

# Modelos
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic

# Bypass SSL nltk
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt', quiet=True)

class ABSAPipeline:
    def __init__(self, bertopic_model_path: str):
        print("Iniciando carregamento dos modelos na memória...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 1. Carregador de Sentimentos Múltiplos (Hugging Face)
        self.sentiment_model_name = "tabularisai/multilingual-sentiment-analysis"
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name)
        self.sentiment_model.eval()  # Garante modo de inferência
        self.sentiment_model.to(self.device)
        
        # Pesos correspondentes às classes do modelo [1 Estrela, 2 Estrelas, 3 Estrelas, 4 Estrelas, 5 Estrelas]
        self.score_weights = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0]).to(self.device)

        # 2. Carregador de Embeddings para BERTopic
        self.embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        # 3. Carregando modelo BERTopic offline treinado
        self.topic_model = BERTopic.load(bertopic_model_path, embedding_model=self.embedding_model)

    def extract_continuous_score(self, text: str) -> float:
        """
        Gera um score de 1.0 a 5.0 usando produto escalar.
        """
        inputs = self.sentiment_tokenizer(text, return_tensors='pt', truncation=True, max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
            
        probs = F.softmax(outputs.logits, dim=-1).squeeze()
        
        # Produto Escalar: (P_1 * 1.0) + (P_2 * 2.0) + ...
        # Assume que o output está na ordem crescente. Ajuste se o modelo não estiver.
        if len(probs) != 5:
            # Fallback se o modelo 'tabularisai' tiver saídas diferentes
            # Se for 3 outputs (Neg, Neu, Pos)
             if len(probs) == 3:
                 temp_weights = torch.tensor([1.0, 3.0, 5.0]).to(self.device)
                 score = torch.dot(probs, temp_weights).item()
                 return score
                 
        score = torch.dot(probs, self.score_weights).item()
        return score

    def simple_sentence_split(self, text: str) -> list[str]:
        # Alternativa nltk para manter compatibilidade com quebras naturais
        frases = nltk.sent_tokenize(text, language='portuguese')
        return [f.strip() for f in frases if len(f.strip()) >= 30]

    def process_reviews(self, raw_reviews: List[Dict[str, Any]], game_details: dict) -> Dict[str, Any]:
        start_time = time.time()

        # 1. Extração de Frases Brutas
        sentences_to_infer = []
        review_ids = []

        for review in raw_reviews:
            r_text = review.get('text', '')
            if not r_text:
                continue

            sentences = self.simple_sentence_split(r_text)
            for sent in sentences:
                sentences_to_infer.append(sent)
                review_ids.append(review.get("id"))

        if not sentences_to_infer:
            return self._build_empty_response(game_details, start_time)

        # 2. Inferência de Tópico (MUITO RÁPIDO)
        # Não re-geramos os embeddings explicitamente pois model.transform fará isso
        # internamente via a property self.embedding_model que atachamos no init.
        topics, _ = self.topic_model.transform(sentences_to_infer)

        # 3. Classificação de Sentimento com Filtro de Ruído (Otimização)
        data_rows = []
        for i, sent in enumerate(sentences_to_infer):
            topic_id = topics[i]

            # Se for ruído (-1), ignora e não gasta inferência do modelo pesado
            if topic_id != -1:
                sent_score = self.extract_continuous_score(sent)

                data_rows.append({
                    "review_id": review_ids[i],
                    "sentence": sent,
                    "review_score": sent_score,
                    "topic_id": topic_id
                })

        if not data_rows:
            return self._build_empty_response(game_details, start_time)

        df_valid = pd.DataFrame(data_rows)

        # 4. Agregação Final usando Pandas
        resultado_final = self._aggregate_results(df_valid, game_details, start_time, len(raw_reviews))

        return resultado_final

    def _aggregate_results(self, df: pd.DataFrame, game_details: dict, start_time: float, num_analyzed: int) -> Dict[str, Any]:
        
        # Filtra os outliers (Ruído, tópico -1)
        df_valid = df[df['topic_id'] != -1]
        
        # Agrupar por Tópico e calcular Média do Score e Contagem
        agg_df = df_valid.groupby('topic_id').agg(
            score=('review_score', 'mean'),
            mentions=('sentence', 'count')
        ).reset_index()

        positive_topics = []
        negative_topics = []
        
        # Score global da review (agregado por review única e não ponderado por qtde de frases)
        unique_reviews = df.drop_duplicates('review_id')
        overall_score = unique_reviews['review_score'].mean() if len(unique_reviews) > 0 else 0

        # Para resgatar as palavras chaves
        topic_info = self.topic_model.get_topic_info()

        for _, row in agg_df.iterrows():
            tid = int(row['topic_id'])
            score = float(row['score'])
            mentions = int(row['mentions'])
            is_positive_topic = score >= 3.0
            
            # Recuperar palavras e quotes
            words_freq = self.topic_model.get_topic(tid)
            keywords = [w[0] for w in words_freq[:3]] if words_freq else [f"Topico {tid}"]
            
            # Extração inteligente de quotes por polaridade do tópico
            df_topic_all = df_valid[df_valid['topic_id'] == tid]

            if is_positive_topic:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] >= 3.0] \
                    .sort_values(by='review_score', ascending=False)
            else:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] < 3.0] \
                    .sort_values(by='review_score', ascending=True)

            # Fallback de segurança: se filtro vier vazio, usa o tópico completo
            if df_topic_filtered.empty:
                quotes = df_topic_all['sentence'].head(2).tolist()
            else:
                quotes = df_topic_filtered['sentence'].head(2).tolist()
                 
            topic_name = " | ".join([k.capitalize() for k in keywords[:3]])

            topic_payload = {
                "topic": topic_name,
                "mentions": mentions,
                "score": round(score, 1),
                "keywords": keywords,
                "quotes": quotes
            }
            
            # Separação por threshold 3.0
            if is_positive_topic:
                positive_topics.append(topic_payload)
            else:
                negative_topics.append(topic_payload)

        # Ordenar por mais menções
        positive_topics = sorted(positive_topics, key=lambda x: x["mentions"], reverse=True)
        negative_topics = sorted(negative_topics, key=lambda x: x["mentions"], reverse=True)

        processing_time = time.time() - start_time

        return {
            "game": {
                "name": game_details.get("name", "Jogo Desconhecido")
            },
            "summary": {
                "overall_score": round(float(overall_score), 1),
                "reviews_analyzed": num_analyzed
            },
            "topics": {
                "positive": positive_topics[:10], # limit top 10
                "negative": negative_topics[:10]
            },
            "metadata": {
                "processing_time_seconds": round(processing_time, 2),
                "model_version": "v2.0-transform-only"
            }
        }
        
    def _build_empty_response(self, game_details, start_time):
        return {
            "game": {"name": game_details.get("name", "Jogo Desconhecido")},
            "summary": {"overall_score": 0.0, "reviews_analyzed": 0},
            "topics": {"positive": [], "negative": []},
            "metadata": {"processing_time_seconds": round(time.time() - start_time, 2), "model_version": "v2.0-transform-only"}
        }

# Inicializador Singleton
# instance = ABSAPipeline("steam_bertopic_model")
