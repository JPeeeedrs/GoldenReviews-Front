"""BERT-based inference pipeline for Golden Reviews."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SENT_MIN_LEN = 35
DEFAULT_BATCH_SIZE = 64



@dataclass
class BertConfig:
    sentiment_model: str
    embedding_model: str
    bertopic_pos_dir: Path
    bertopic_neg_dir: Path
    sentence_min_len: int = DEFAULT_SENT_MIN_LEN
    batch_size: int = DEFAULT_BATCH_SIZE


class BertPipeline:
    def __init__(self, config: BertConfig) -> None:
        self._config = config
        self._sentiment_analyzer = None
        self._topic_model_pos = None
        self._topic_model_neg = None
        self._embedding_model = None

    def is_loaded(self) -> bool:
        return self._sentiment_analyzer is not None

    def load(self) -> None:
        """Load models once and keep them in memory."""
        if self._sentiment_analyzer is not None:
            return

        from pysentimiento import create_analyzer
        from sentence_transformers import SentenceTransformer
        from bertopic import BERTopic

        self._embedding_model = SentenceTransformer(self._config.embedding_model)
        self._sentiment_analyzer = create_analyzer(
            task="sentiment",
            lang="pt",
            model_name=self._config.sentiment_model,
        )
        self._topic_model_pos = BERTopic.load(
            str(self._config.bertopic_pos_dir),
            embedding_model=self._embedding_model,
        )
        self._topic_model_neg = BERTopic.load(
            str(self._config.bertopic_neg_dir),
            embedding_model=self._embedding_model,
        )

    def analyze(self, reviews: list[dict]) -> dict:
        """Run sentiment and topic inference on reviews."""
        self.load()

        sentences = list(self._iter_sentences(reviews))
        if not sentences:
            return {
                "by_topic": {},
                "highlights": {"positive": [], "negative": []},
            }

        (
            pos_sents,
            neg_sents,
            neu_sents,
            pos_highlights,
            neg_highlights,
        ) = self._predict_sentiment(sentences)

        by_topic = {"positive": {}, "negative": {}}

        pos_topics = []
        if pos_sents:
            pos_topics_raw, _ = self._topic_model_pos.transform(pos_sents)
            # Fix off-by-one BERTopic index shift caused by reduce_outliers / embeddings strategy
            pos_topics = [t - 1 for t in pos_topics_raw]
            by_topic["positive"] = self._group_by_topic(pos_sents, pos_topics)

        neg_topics = []
        if neg_sents:
            neg_topics_raw, _ = self._topic_model_neg.transform(neg_sents)
            # Fix off-by-one BERTopic index shift caused by reduce_outliers / embeddings strategy
            neg_topics = [t - 1 for t in neg_topics_raw]
            by_topic["negative"] = self._group_by_topic(neg_sents, neg_topics)

        review_dump = []
        for sent, topic_id in zip(pos_sents, pos_topics):
            topic_int = int(topic_id)
            review_dump.append(
                {
                    "sentence": sent,
                    "sentiment": "POS",
                    "topic_id": topic_int,
                    "category": self.topic_label(topic_int, "positive"),
                    "topic_label": self.topic_label(topic_int, "positive"),
                    "topic_label_prev": self.topic_label(topic_int - 1, "positive")
                    if topic_int > 0
                    else None,
                }
            )
        for sent, topic_id in zip(neg_sents, neg_topics):
            topic_int = int(topic_id)
            review_dump.append(
                {
                    "sentence": sent,
                    "sentiment": "NEG",
                    "topic_id": topic_int,
                    "category": self.topic_label(topic_int, "negative"),
                    "topic_label": self.topic_label(topic_int, "negative"),
                    "topic_label_prev": self.topic_label(topic_int - 1, "negative")
                    if topic_int > 0
                    else None,
                }
            )
        for sent in neu_sents:
            review_dump.append(
                {
                    "sentence": sent,
                    "sentiment": "NEU",
                    "topic_id": None,
                    "category": "Sem categoria",
                }
            )

        return {
            "by_topic": by_topic,
            "highlights": {
                "positive": pos_highlights[:8],
                "negative": neg_highlights[:8],
            },
            "review_dump": review_dump,
        }

    def topic_label(self, topic_id: int, polarity: str) -> str:
        self.load()

        if topic_id == -1:
            return "Topico geral"

        model = self._topic_model_pos if polarity == "positive" else self._topic_model_neg
        topic = model.get_topic(topic_id) if model is not None else None
        if not topic:
            return f"Topico {topic_id}"

        words = [word for word, _ in topic[:3]]
        if not words:
            return f"Topico {topic_id}"
        return f"Topico {topic_id}: {', '.join(words)}"

    def _iter_sentences(self, reviews: list[dict]) -> Iterable[str]:
        for review in reviews:
            text = (review.get("text") or "").strip()
            for sentence in simple_sentence_split(text):
                sentence = sentence.strip()
                if len(sentence) < self._config.sentence_min_len:
                    continue
                yield sentence

    def _predict_sentiment(self, sentences: list[str]):
        pos_sents = []
        neg_sents = []
        neu_sents = []
        pos_highlights = []
        neg_highlights = []

        batch_size = self._config.batch_size
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i : i + batch_size]
            result = self._sentiment_analyzer.predict(batch)
            labels = result.output if hasattr(result, "output") else result
            for sent, label in zip(batch, labels):
                if hasattr(label, "output"):
                    label = label.output
                if label == "POS":
                    pos_sents.append(sent)
                    pos_highlights.append(sent)
                elif label == "NEG":
                    neg_sents.append(sent)
                    neg_highlights.append(sent)
                else:
                    neu_sents.append(sent)

        return pos_sents, neg_sents, neu_sents, pos_highlights, neg_highlights

    @staticmethod
    def _group_by_topic(sentences: list[str], topics: list[int]):
        grouped = {}
        for sent, topic_id in zip(sentences, topics):
            key = str(topic_id)
            grouped.setdefault(key, []).append(sent)
        return grouped


def simple_sentence_split(text: str) -> list[str]:
    if not text:
        return []

    sentences = []
    current = []
    for ch in text:
        current.append(ch)
        if ch in ".!?":
            sentences.append("".join(current))
            current = []

    if current:
        sentences.append("".join(current))

    return sentences
