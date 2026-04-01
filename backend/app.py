"""Flask backend para análise de reviews da Steam."""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from typing import Any, Callable, Optional

import requests
import spacy
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={app_id}&l=portuguese"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAMSPY_DETAILS_URL = "https://steamspy.com/api.php"

TOPICS: dict[str, list[str]] = {
    "🐛 bugs e crashes": [
        "bug",
        "bugs",
        "bugado",
        "bugada",
        "bugar",
        "bugou",
        "crash",
        "crasha",
        "crashou",
        "crashando",
        "travou",
        "trava",
        "travando",
        "glitch",
        "glitches",
        "erro",
        "erros",
        "falha",
        "falhas",
        "não abre",
        "não inicia",
        "não funciona",
        "não roda",
        "loop infinito",
        "tela preta",
        "softlock",
    ],
    "📉 desempenho e FPS": [
        "fps",
        "lag",
        "lags",
        "lagando",
        "desempenho",
        "performance",
        "otimização",
        "otimizado",
        "frames",
        "framerate",
        "stuttering",
        "engasga",
        "lento",
        "pesado",
        "queda de fps",
        "drops",
    ],
    "🌐 servidores e online": [
        "servidor",
        "servidores",
        "online",
        "multiplayer",
        "matchmaking",
        "fila de espera",
        "conexão",
        "desconectado",
        "ping",
        "latência",
        "ranked",
        "lobby",
        "cross-play",
        "p2p",
        "dedicado",
    ],
    "🎨 gráficos e visual": [
        "gráfico",
        "gráficos",
        "visual",
        "arte",
        "bonito",
        "lindo",
        "feio",
        "animação",
        "textura",
        "resolução",
        "iluminação",
        "sombras",
        "ray tracing",
    ],
    "🎮 gameplay e mecânicas": [
        "gameplay",
        "mecânica",
        "jogabilidade",
        "controles",
        "combate",
        "movimentação",
        "progressão",
        "habilidade",
        "responsivo",
    ],
    "📖 história e narrativa": [
        "história",
        "enredo",
        "narrativa",
        "roteiro",
        "personagem",
        "lore",
        "trama",
        "final",
        "missão",
        "diálogo",
    ],
    "📦 conteúdo e duração": [
        "conteúdo",
        "duração",
        "curto",
        "longo",
        "horas de jogo",
        "repetitivo",
        "mapa",
        "mundo",
        "replayability",
        "end game",
        "grind",
    ],
    "💰 preço e monetização": [
        "preço",
        "valor",
        "caro",
        "barato",
        "vale a pena",
        "promoção",
        "dlc",
        "microtransação",
        "pay to win",
        "loot box",
        "compra",
        "grátis",
    ],
    "🔊 som e trilha": [
        "som",
        "sons",
        "música",
        "trilha",
        "áudio",
        "dublagem",
        "voz",
        "efeitos sonoros",
    ],
    "🛠️ suporte e desenvolvedores": [
        "suporte",
        "desenvolvedor",
        "dev",
        "atualização",
        "patch",
        "abandonado",
        "comunidade",
        "cheater",
        "anti-cheat",
    ],
    "😄 diversão e imersão": [
        "divertido",
        "viciante",
        "imersivo",
        "entretenimento",
        "incrível",
        "maravilhoso",
        "épico",
        "obra prima",
    ],
    "📚 tutorial e curva de aprendizado": [
        "tutorial",
        "difícil",
        "fácil",
        "acessível",
        "aprender",
        "complexo",
        "curva de aprendizado",
    ],
}

BLACKLIST_CHUNKS = {
    "jogo",
    "game",
    "jogos",
    "games",
    "eu",
    "você",
    "ele",
    "ela",
    "coisa",
    "coisas",
    "parte",
    "partes",
    "muito",
    "pouco",
    "vez",
    "vezes",
    "steam",
    "valve",
    "esse",
    "essa",
    "isso",
}

NEGATIVE_MARKERS = [
    "não funciona",
    "nao funciona",
    "não roda",
    "nao roda",
    "não abre",
    "crashando",
    "travando",
    "bugado",
    "péssimo",
    "horrível",
    "insuportável",
    "lixo",
]

POSITIVE_IN_NEG = [
    "boa história",
    "bons gráficos",
    "boa gameplay",
    "mas a história",
    "porém o gameplay",
    "apesar",
    "pelo menos",
    "ponto positivo",
]


def load_nlp() -> spacy.Language:
    try:
        return spacy.load("pt_core_news_sm")
    except OSError as exc:
        raise RuntimeError(
            "Modelo spaCy 'pt_core_news_sm' não encontrado. "
            "Instale com: python -m spacy download pt_core_news_sm"
        ) from exc


NLP = load_nlp()


# ════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def fetch_game_details(app_id: str) -> dict[str, Any]:
    steamspy_data = fetch_steamspy_stats(app_id)
    try:
        resp = requests.get(
            STEAM_DETAILS_URL.format(app_id=app_id),
            timeout=8,
        )
        data = resp.json().get(str(app_id), {})
        if data.get("success"):
            info = data.get("data", {})
            price = info.get("price_overview", {})
            return {
                "appid": str(app_id),
                "name": info.get("name", f"App {app_id}"),
                "header_image": info.get("header_image"),
                "release_date": info.get("release_date", {}).get("date"),
                "price": price.get("final_formatted") or price.get("final"),
                "owners": info.get("owners") or steamspy_data.get("owners"),
                "total_reviews": (
                    info.get("recommendations", {}).get("total")
                    or steamspy_data.get("total_reviews")
                ),
                "metacritic": (info.get("metacritic", {}) or {}).get("score"),
                "genres": [g.get("description") for g in info.get("genres", [])][:3],
                "short_description": info.get("short_description"),
                "steamspy": steamspy_data,
            }
    except requests.RequestException:
        pass
    return {
        "appid": str(app_id),
        "name": f"App {app_id}",
        "owners": steamspy_data.get("owners"),
        "total_reviews": steamspy_data.get("total_reviews"),
        "steamspy": steamspy_data,
    }


def fetch_steamspy_stats(app_id: str) -> dict[str, Any]:
    params = {"request": "appdetails", "appid": app_id}
    try:
        resp = requests.get(STEAMSPY_DETAILS_URL, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        positive = int(data.get("positive", 0) or 0)
        negative = int(data.get("negative", 0) or 0)
        return {
            "owners": data.get("owners"),
            "total_reviews": positive + negative,
            "positive_reviews": positive,
            "negative_reviews": negative,
        }
    except (requests.RequestException, ValueError):
        return {}


def fetch_reviews(
    app_id: str,
    max_reviews: int = 0,
    language: str = "brazilian",
) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    seen: set[str] = set()
    cursor = "*"
    errors = 0
    MAX_ERRORS = 5
    url = STEAM_REVIEWS_URL.format(app_id=app_id)

    while True:
        params = {
            "json": 1,
            "language": language,
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": 100,
            "filter": "recent",
            "cursor": cursor,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            errors = 0
        except requests.Timeout:
            errors += 1
            if errors >= MAX_ERRORS:
                break
            time.sleep(3)
            continue
        except (requests.RequestException, ValueError):
            errors += 1
            if errors >= MAX_ERRORS:
                break
            time.sleep(3)
            continue

        if data.get("success") != 1:
            break

        batch = data.get("reviews", [])
        if not batch:
            break

        for review in batch:
            rid = str(review.get("recommendationid", ""))
            text = (review.get("review") or "").strip()

            if not rid or rid in seen or len(text) < 40:
                continue

            seen.add(rid)
            author = review.get("author", {})
            reviews.append(
                {
                    "id": rid,
                    "text": text,
                    "recommended": bool(review.get("voted_up", False)),
                    "hours": int(author.get("playtime_forever", 0)) // 60,
                    "votes_helpful": int(review.get("votes_up", 0)),
                }
            )

            if max_reviews and len(reviews) >= max_reviews:
                return reviews

        cursor = data.get("cursor", "")
        if not cursor:
            break

        time.sleep(0.35)

    return reviews


def _topics_from_sentence(sentence: str) -> list[str]:
    lower = sentence.lower()
    found: list[str] = []
    for topic, keywords in TOPICS.items():
        if any(keyword in lower for keyword in keywords):
            found.append(topic)
    return found


def _sentence_sentiment(sentence: str, review_positive: bool) -> str:
    lower = sentence.lower()
    sentiment = "positivo" if review_positive else "negativo"
    if review_positive:
        if any(marker in lower for marker in NEGATIVE_MARKERS):
            return "negativo"
    else:
        if any(marker in lower for marker in POSITIVE_IN_NEG):
            return "positivo"
    return sentiment


def _sentence_quality(sentence: str) -> float:
    length = len(sentence)
    if length < 40:
        return 0.0
    if length > 400:
        return 0.6
    score = min(length / 200, 1.0)
    if re.search(r"\d+", sentence):
        score += 0.1
    if re.search(r"capítulo|missão|fase|nível|mapa|chefe|boss", sentence, re.I):
        score += 0.1
    return min(score, 1.0)


def _deduplicate(sentences: list[str]) -> list[str]:
    selected: list[str] = []
    for sentence in sentences:
        current = set(sentence.lower().split())
        duplicate = False
        for existing in selected:
            words_existing = set(existing.lower().split())
            union = current | words_existing
            if union and len(current & words_existing) / len(union) > 0.65:
                duplicate = True
                break
        if not duplicate:
            selected.append(sentence)
    return selected


def _relevant_chunks(doc: spacy.tokens.Doc) -> list[str]:
    chunks: list[str] = []
    for chunk in doc.noun_chunks:
        text = chunk.text.strip().lower()
        tokens = text.split()
        if len(tokens) < 2:
            continue
        if all(token in BLACKLIST_CHUNKS for token in tokens):
            continue
        if tokens[0] in BLACKLIST_CHUNKS:
            continue
        chunks.append(text)
    return chunks


def analyze_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_topic: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"positivo": [], "negativo": []}
    )
    chunks_pos: Counter[str] = Counter()
    chunks_neg: Counter[str] = Counter()
    positive_sentences: list[str] = []
    negative_sentences: list[str] = []

    for review in reviews:
        text = review["text"]
        is_positive = review["recommended"]
        doc = NLP(text[:6000])

        for sent in doc.sents:
            sentence = sent.text.strip()
            if len(sentence) < 35:
                continue

            topics = _topics_from_sentence(sentence)
            sentiment = _sentence_sentiment(sentence, is_positive)

            phrase_doc = NLP(sentence)
            for chunk in _relevant_chunks(phrase_doc):
                if sentiment == "positivo":
                    chunks_pos[chunk] += 1
                else:
                    chunks_neg[chunk] += 1

            if sentiment == "positivo":
                positive_sentences.append(sentence)
            else:
                negative_sentences.append(sentence)

            if not topics:
                continue

            for topic in topics:
                bucket = by_topic[topic][sentiment]
                if sentence not in bucket:
                    bucket.append(sentence)

    def _post_process(sentences: list[str]) -> list[str]:
        return _deduplicate(
            sorted(sentences, key=_sentence_quality, reverse=True)
        )

    for topic in by_topic:
        for sentiment in ("positivo", "negativo"):
            by_topic[topic][sentiment] = _post_process(by_topic[topic][sentiment])

    return {
        "por_topico": dict(by_topic),
        "chunks_positivos": chunks_pos.most_common(25),
        "chunks_negativos": chunks_neg.most_common(25),
        "destaques": {
            "positivo": _post_process(positive_sentences)[:8],
            "negativo": _post_process(negative_sentences)[:8],
        },
    }


def summarize_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(reviews)
    positive = sum(1 for r in reviews if r["recommended"])
    negative = total - positive
    pct_positive = round((positive * 100 / total), 1) if total else 0
    avg_hours = round(sum(r["hours"] for r in reviews) / total, 1) if total else 0
    return {
        "collected": total,
        "positive": {"count": positive, "percent": pct_positive},
        "negative": {"count": negative, "percent": round(100 - pct_positive, 1)},
        "avg_hours": avg_hours,
    }


# ════════════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════════════


@app.route("/reviews")
def reviews_endpoint():
    appid = (request.args.get("appid") or "").strip()
    if not appid:
        return jsonify({"error": "Parâmetro 'appid' é obrigatório."}), 400

    max_reviews = int(request.args.get("maxReviews", 1200))
    language = request.args.get("language", "brazilian")

    reviews = fetch_reviews(appid, max_reviews, language)
    if not reviews:
        return jsonify({"error": "Nenhuma review encontrada no idioma solicitado."}), 404

    analysis = analyze_reviews(reviews)
    summary = summarize_reviews(reviews)
    game = fetch_game_details(appid)

    topics_payload = [
        {
            "name": topic,
            "positive": {
                "count": len(data["positivo"]),
                "examples": data["positivo"][:5],
            },
            "negative": {
                "count": len(data["negativo"]),
                "examples": data["negativo"][:5],
            },
        }
        for topic, data in analysis["por_topico"].items()
    ]

    return jsonify(
        {
            "game": game,
            "summary": summary,
            "highlights": analysis["destaques"],
            "topics": topics_payload,
            "keywords": {
                "positive": analysis["chunks_positivos"],
                "negative": analysis["chunks_negativos"],
            },
            "meta": {
                "language": language,
                "maxReviewsRequested": max_reviews,
            },
            "aiConsistency": {
                "status": "pending",
                "message": "Validador semântico será habilitado em breve.",
            },
        }
    )



def _default_capsule(appid: str) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_184x69.jpg"


@app.route("/search")
def search():
    term = request.args.get("q", "")
    if len(term) < 2:
        return jsonify([])

    params = {"term": term, "l": "portuguese", "cc": "BR"}
    try:
        res = requests.get(STEAM_SEARCH_URL, params=params, timeout=5)
        data = res.json()
    except requests.RequestException:
        return jsonify({"error": "Erro na Steam"}), 502

    items = data.get("items", [])
    results: list[dict[str, Any]] = []
    for item in items[:8]:
        appid = item.get("appid") or item.get("id")
        if not appid:
            continue
        appid = str(appid)
        image = (
            item.get("large_capsule_image")
            or item.get("capsule_image")
            or item.get("header_image")
        )
        if not image:
            image = _default_capsule(appid)
        results.append(
            {
                "appid": appid,
                "name": item.get("name"),
                "image": image,
            }
        )

    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)