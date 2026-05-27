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
        # 1. Carregador de Sentimentos Múltiplos (Hugging Face)
        self.sentiment_model_name = "tabularisai/multilingual-sentiment-analysis"
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name)
        # Pesos correspondentes às classes do modelo [1 Estrela, 2 Estrelas, 3 Estrelas, 4 Estrelas, 5 Estrelas] (geralmente essa é a ordem)
        self.score_weights = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])

        # 2. Carregador de Embeddings para BERTopic
        self.embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        # 3. Carregando modelo BERTopic offline treinado
        self.topic_model = BERTopic.load(bertopic_model_path, embedding_model=self.embedding_model)

    def extract_continuous_score(self, text: str) -> float:
        """
        Gera um score de 1.0 a 5.0 usando produto escalar.
        """
        inputs = self.sentiment_tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
            
        probs = F.softmax(outputs.logits, dim=-1).squeeze()
        
        # Produto Escalar: (P_1 * 1.0) + (P_2 * 2.0) + ...
        # Assume que o output está na ordem crescente. Ajuste se o modelo não estiver.
        if len(probs) != 5:
            # Fallback se o modelo 'tabularisai' tiver saídas diferentes
            # Se for 3 outputs (Neg, Neu, Pos)
             if len(probs) == 3:
                 temp_weights = torch.tensor([1.0, 3.0, 5.0])
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
        
        # Estrutura para Dataframe
        data_rows = []
        
        # 1 e 2. Sentimento da Review e Herança
        for review in raw_reviews:
            r_text = review.get('text', '')
            if not r_text: continue
            
            review_score = self.extract_continuous_score(r_text)
            
            # Fatiamento e Herança
            sentences = self.simple_sentence_split(r_text)
            for sent in sentences:
                data_rows.append({
                    "review_id": review.get("id"),
                    "sentence": sent,
                    "review_score": review_score
                })
        
        if not data_rows:
            return self._build_empty_response(game_details, start_time)

        df = pd.DataFrame(data_rows)
        
        # 3. Inferência do Tópico usando model.transform() (MUITO RÁPIDO)
        sentences_to_infer = df['sentence'].tolist()
        # Não re-geramos os embeddings explicitamente pois model.transform fará isso 
        # internamente via a property self.embedding_model que atachamos no init.
        topics, _ = self.topic_model.transform(sentences_to_infer)
        
        df['topic_id'] = topics
        
        # 4. Agregação Final usando Pandas
        resultado_final = self._aggregate_results(df, game_details, start_time, len(raw_reviews))
        
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
        
        # Para resgatar as palavras chaves
        topic_info = self.topic_model.get_topic_info()
        
        overall_score = df['review_score'].mean() if len(df) > 0 else 0

        for _, row in agg_df.iterrows():
            tid = int(row['topic_id'])
            score = float(row['score'])
            mentions = int(row['mentions'])
            
            # Recuperar palavras e quotes
            words_freq = self.topic_model.get_topic(tid)
            keywords = [w[0] for w in words_freq[:3]] if words_freq else [f"Topico {tid}"]
            
            # Encontrar frases representativas
            rep_docs = self.topic_model.get_representative_docs(tid)
            
            # Se não houver rep_docs, buscar diretamente no DF para ter amostras
            if not rep_docs:
                 amostras = df[df['topic_id'] == tid]['sentence'].head(2).tolist()
                 quotes = amostras
            else:
                 quotes = rep_docs[:2]
                 
            topic_name = " | ".join([k.capitalize() for k in keywords[:3]])

            topic_payload = {
                "topic": topic_name,
                "mentions": mentions,
                "score": round(score, 1),
                "keywords": keywords,
                "quotes": quotes
            }
            
            # Separação por threshold 3.0
            if score >= 3.0:
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
