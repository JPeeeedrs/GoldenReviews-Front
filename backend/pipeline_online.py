from __future__ import annotations
import nltk
import ssl
import pandas as pd
from typing import Any, Dict, List
import time
import torch
import torch.nn.functional as F

from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic

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
        

        self.sentiment_model_name = "tabularisai/multilingual-sentiment-analysis"
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name)
        self.sentiment_model.eval()
        self.sentiment_model.to(self.device)
        

        self.score_weights = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0]).to(self.device)

        self.embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


        self.topic_model = BERTopic.load(bertopic_model_path, embedding_model=self.embedding_model)

    def extract_continuous_score(self, text: str) -> float:

        inputs = self.sentiment_tokenizer(text, return_tensors='pt', truncation=True, max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
            
        probs = F.softmax(outputs.logits, dim=-1).squeeze()
        

        if len(probs) != 5:

             if len(probs) == 3:
                 temp_weights = torch.tensor([1.0, 3.0, 5.0]).to(self.device)
                 score = torch.dot(probs, temp_weights).item()
                 return score
                 
        score = torch.dot(probs, self.score_weights).item()
        return score

    def simple_sentence_split(self, text: str) -> list[str]:

        frases = nltk.sent_tokenize(text, language='portuguese')
        return [f.strip() for f in frases if len(f.strip()) >= 30]

    def process_reviews(self, raw_reviews: List[Dict[str, Any]], game_details: dict) -> Dict[str, Any]:
        start_time = time.time()

        sentences_to_infer = []
        review_ids = []

        review_hours_map = {r.get("id"): r.get("hours", 0) for r in raw_reviews}

        total_hours = sum(review_hours_map.values())
        total_reviews = len(review_hours_map)
        avg_hours_dataset = (total_hours / total_reviews) if total_reviews > 0 else 1.0

        avg_hours_dataset = max(avg_hours_dataset, 1.0)

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

        topics, _ = self.topic_model.transform(sentences_to_infer)

        data_rows = []
        for i, sent in enumerate(sentences_to_infer):
            topic_id = topics[i]

            if topic_id != -1:
                sent_score = self.extract_continuous_score(sent)

                hours_played = review_hours_map.get(review_ids[i], 0)

                razao_horas = min(hours_played / avg_hours_dataset, 3.0)

                peso_review = 0.5 + (0.5 * razao_horas)

                data_rows.append({
                    "review_id": review_ids[i],
                    "sentence": sent,
                    "review_score": sent_score,
                    "topic_id": topic_id,
                    "weight": peso_review,
                    "weighted_score": sent_score * peso_review
                })

        if not data_rows:
            return self._build_empty_response(game_details, start_time)

        df_valid = pd.DataFrame(data_rows)

        resultado_final = self._aggregate_results(df_valid, game_details, start_time, len(raw_reviews))

        return resultado_final

    def _aggregate_results(self, df: pd.DataFrame, game_details: dict, start_time: float, num_analyzed: int) -> Dict[str, Any]:
        
        df_valid = df[df['topic_id'] != -1]
        
        agg_df = df_valid.groupby('topic_id').apply(
            lambda g: pd.Series({
                # Soma das notas ponderadas / Soma dos pesos
                'score': g['weighted_score'].sum() / g['weight'].sum() if g['weight'].sum() > 0 else g['review_score'].mean(),
                'mentions': len(g)
            })
        ).reset_index()
        positive_topics = []
        negative_topics = []
        
        unique_reviews = df.drop_duplicates('review_id')
        if len(unique_reviews) > 0 and unique_reviews['weight'].sum() > 0:
            overall_score = unique_reviews['weighted_score'].sum() / unique_reviews['weight'].sum()
        else:
            overall_score = 0

        topic_info = self.topic_model.get_topic_info()

        for _, row in agg_df.iterrows():
            tid = int(row['topic_id'])
            score = float(row['score'])
            mentions = int(row['mentions'])
            is_positive_topic = score >= 3.0
            
            words_freq = self.topic_model.get_topic(tid)
            keywords = [w[0] for w in words_freq[:3]] if words_freq else [f"Topico {tid}"]
            

            df_topic_all = df_valid[df_valid['topic_id'] == tid]

            if is_positive_topic:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] >= 3.0] \
                    .sort_values(by='review_score', ascending=False)
            else:
                df_topic_filtered = df_topic_all[df_topic_all['review_score'] < 3.0] \
                    .sort_values(by='review_score', ascending=True)

            if df_topic_filtered.empty:
                quotes = df_topic_all['sentence'].head(2).tolist()
            else:
                quotes = df_topic_filtered['sentence'].head(2).tolist()
                 
            topic_name = " | ".join([k.capitalize() for k in keywords[:3]])

            topic_payload = {
                "topic": topic_name,
                "topic_id": tid,
                "mentions": mentions,
                "score": round(score, 1),
                "keywords": keywords,
                "quotes": quotes
            }
            
            if is_positive_topic:
                positive_topics.append(topic_payload)
            else:
                negative_topics.append(topic_payload)


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
                "positive": positive_topics[:10], 
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

