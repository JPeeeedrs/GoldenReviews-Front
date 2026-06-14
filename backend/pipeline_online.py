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
        self.sentiment_model_name = "pysentimiento/bertweet-pt-sentiment"
        self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
        self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name)
        self.sentiment_model.eval()

        if self.device.type == 'cpu':
            print("CPU detectada — aplicando quantização dinâmica (reduz RAM ~50%)...")   
            self.sentiment_model = torch.quantization.quantize_dynamic(self.sentiment_model,{torch.nn.Linear}, dtype=torch.qint8)
            print("Quantização aplicada com sucesso!")

        self.sentiment_model.to(self.device)
        
        label_to_score = {"NEG": 1.0, "NEU": 3.0, "POS": 5.0}
        
        weights_list = []
        for i in range(len(self.sentiment_model.config.id2label)):
            label_name = self.sentiment_model.config.id2label[i]
            weights_list.append(label_to_score.get(label_name, 3.0)) 
            
        self.score_weights = torch.tensor(weights_list).to(self.device)

        self.embedding_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.topic_model = BERTopic.load(bertopic_model_path, embedding_model=self.embedding_model)
        print("Todos os modelos carregados.")

    def extract_scores_batch(self, texts: list[str], batch_size: int = 32) -> list[float]:

        all_scores: list[float] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            inputs = self.sentiment_tokenizer(
                batch, 
                return_tensors = "pt", 
                truncation = True, 
                max_length = 128,
                padding = True,
                ).to(self.device)

            with torch.no_grad():
                outputs = self.sentiment_model(**inputs)
            
            probs = F.softmax(outputs.logits, dim=-1)
        
            scores = torch.mv(probs, self.score_weights)

            all_scores.extend(scores.tolist())

        return all_scores

    def simple_sentence_split(self, text: str) -> list[str]:# Divide o texto em sentenças usando nltk, filtrando sentenças muito curtas.

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

        avg_hours_dataset = max(avg_hours_dataset, 1.0) # Evita divisão por zero e mantém uma média mínima de 1 hora para o cálculo do peso, garantindo que reviews sem horas ou com horas muito baixas ainda tenham um peso razoável.

        for review in raw_reviews:
            r_text = review.get('text', '')
            if not r_text:
                continue

            sentences = self.simple_sentence_split(r_text)
            for sent in sentences:
                sentences_to_infer.append(sent)
                review_ids.append(review.get("id"))

        if not sentences_to_infer: # Se a lista de sentenças estiver vazia, aciona a função que contrói uma resposta padrão vazia . 
            return self._build_empty_response(game_details, start_time)

        t1 = time.time()
        topics, _ = self.topic_model.transform(sentences_to_infer) # Passa a lista de sentenças para o BERTopic processar e retornar os tópicos correspondentes a cada sentença. Observação: o _ depois do topics é uma forma de ignogar o segundo valor que o BERTopic retorna, que é a probabilidade que ele definiu de cada sentença pertencer a cada tópico. No momento não estamos utilizando por uma questão de praticidade mais talvez possa ser útil no futuro para filtrar sentenças com baixa confiança de classificação.
        print(f"[Timer] BERTopic transform: {time.time() - t1:.2f}s")
    

        valid_items = []
        for i, sent in enumerate(sentences_to_infer):
            topic_id = topics[i]

            if topic_id == -1:
                continue 
            hours_played = review_hours_map.get(review_ids[i], 0)

            valid_items.append({
                "sentence": sent,
                "topic_id": topic_id,
                "review_id": review_ids[i],
                "hours_played": hours_played,
            })

        if not valid_items:
            return self._build_empty_response(game_details, start_time)

        valid_texts = [item["sentence"] for item in valid_items]
        print(f"[Pipeline] Rodando sentimento em batch: {len(valid_texts)} frases válidas...")

        t2 = time.time()
        scores = self.extract_scores_batch(valid_texts, batch_size = 32)
        print(f"[Timer] Sentiment batch ({len(valid_texts)} frases): {time.time() - t2:.2f}s")

        data_rows = []
        for item, score in zip(valid_items, scores):
            razao_horas = min(item["hours_played"] / avg_hours_dataset, 3.0)
            peso_review = 0.5 + (0.5 * razao_horas)

            data_rows.append({
                "review_id": item["review_id"],
                "sentence": item["sentence"],
                "review_score": score,
                "topic_id": item["topic_id"],
                "weight": peso_review,
                "weighted_score": score * peso_review
            })

        if not data_rows:
            return self._build_empty_response(game_details, start_time)

        df_valid = pd.DataFrame(data_rows)

        t3 = time.time()
        resultado_final = self._aggregate_results(df_valid, game_details, start_time, len(raw_reviews))
        print(f"[Timer] Agregação pandas: {time.time() - t3:.2f}s")

        print(f"[Timer] TOTAL pipeline: {time.time() - start_time:.2f}s")
        return resultado_final

    def _aggregate_results(self, df: pd.DataFrame, game_details: dict, start_time: float, num_analyzed: int) -> Dict[str, Any]:
        
        df_valid = df[df['topic_id'] != -1]
            
            # Aplicando a abordagem da média dos jogadores para a nota dos tópicos também . 
            # O código abaixo tá basicamente usando o Pandas para criar uma "nova" tabela onde todas as frases de uma review/id são fundidas em uma média. 
        df_topico_por_review = df_valid.groupby(['review_id', 'topic_id']).agg({
            'review_score': 'mean',  
            'weight': 'first'       
        }).reset_index()
        
        # Aqui ta calculando a nota ponderada com os pesos(tempo de jogo) dessa tabela temporária com as notas unificadas 
        df_topico_por_review['weighted_score'] = df_topico_por_review['review_score'] * df_topico_por_review['weight']
        
        # Aqui ele ta fazendo a média que da o resultado da nota do tópico 
        agg_df = df_topico_por_review.groupby('topic_id').apply(
            lambda g: pd.Series({
                'score': g['weighted_score'].sum() / g['weight'].sum() if g['weight'].sum() > 0 else g['review_score'].mean(),
                'mentions': len(g)  # Como cada linha já é um jogador único, len(g) é o total de pessoas!
            })
        ).reset_index()
        positive_topics = []
        negative_topics = []
        # Alteração do cálculo do score geral. O código anterior possua um erro gravíssimo que literalmente pegava somente a primeira sentença de um grupo de sentenças da mesma review e jogava todo o resto fora. O correto e fazer a média de todas as sentenças da review e depois aplicar o peso. Isso impede que por exemplo que uma das sentenças do usuário seja positva e tenha várias outras muito negativas que vão ser totalmente desconsideradas. 
        if not df.empty:
            df_por_review = df.groupby('review_id').agg({
                'review_score': 'mean',
                'weight': 'first'
            })
            df_por_review['weighted_score'] = df_por_review['review_score'] * df_por_review['weight']
            overall_score = df_por_review['weighted_score'].sum() / df_por_review['weight'].sum() if df_por_review['weight'].sum() > 0 else 0
        else:
            overall_score = 0

        # topic_info = self.topic_model.get_topic_info() -> comentado pois não estava sendo utilizado 


        # É aqui que o sistema da definindo o nome dos tópicos, pegando as palavras mais frequentes de cada tópico e utilizando elas para criar um nome mais amigável. Bom saber! 
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
                    .sort_values(by='review_score', ascending=False) # Analisar possível mudança do 3.0 para algo como 2.5 ? 
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
                "keywords": keywords, # pode ser usado para nuvem de palavras 
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

