"""Flask backend para análise de reviews da Steam."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from bert_pipeline import BertConfig, BertPipeline


app = Flask(__name__)
CORS(app)


# ════════════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════════════

STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={app_id}&l=portuguese"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAMSPY_DETAILS_URL = "https://steamspy.com/api.php"

BASE_DIR = Path(__file__).resolve().parent
BERT_MODELS_DIR = (
    BASE_DIR
    / ".."
    / "sandbox"
    / "pacotao_golden_review"
    / "models"
    / "bertopic"
).resolve()

BERT_CONFIG = BertConfig(
    sentiment_model="pysentimiento/bertweet-pt-sentiment",
    embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    bertopic_pos_dir=BERT_MODELS_DIR / "ludoprism_positivo_dir",
    bertopic_neg_dir=BERT_MODELS_DIR / "ludoprism_negativo_dir",
)

BERT_PIPELINE = BertPipeline(BERT_CONFIG)


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


def analyze_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    result = BERT_PIPELINE.analyze(reviews)
    topics = _build_topics_payload(result["by_topic"])
    _write_review_dump(result.get("review_dump", []))
    return {
        "topics": topics,
        "highlights": {
            "positivo": result["highlights"]["positive"],
            "negativo": result["highlights"]["negative"],
        },
    }


def _build_topics_payload(by_topic: dict[str, dict[str, list[str]]]):
    pos_groups = by_topic.get("positive", {})
    neg_groups = by_topic.get("negative", {})

    payload = []
    
    # Processar tópicos positivos (modelo positivo)
    for topic_id, examples in pos_groups.items():
        if str(topic_id) == "-1":
            continue
            
        label = BERT_PIPELINE.topic_label(int(topic_id), "positive")
        payload.append(
            {
                "name": label,
                "positive": {
                    "count": len(examples),
                    "examples": examples[:5],
                },
                "negative": {
                    "count": 0,
                    "examples": [],
                },
            }
        )
        
    # Processar tópicos negativos (modelo negativo)
    for topic_id, examples in neg_groups.items():
        if str(topic_id) == "-1":
            continue
            
        label = BERT_PIPELINE.topic_label(int(topic_id), "negative")
        payload.append(
            {
                "name": label,
                "positive": {
                    "count": 0,
                    "examples": [],
                },
                "negative": {
                    "count": len(examples),
                    "examples": examples[:5],
                },
            }
        )

    return payload


def _write_review_dump(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    output_dir = BASE_DIR / "analysis_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "reviews_analysis.json"
    output_path.write_text(
        json.dumps(rows, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


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

    return jsonify(
        {
            "game": game,
            "summary": summary,
            "highlights": analysis["highlights"],
            "topics": analysis["topics"],
            "keywords": {
                "positive": [],
                "negative": [],
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