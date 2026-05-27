"""FastAPI backend for Steam review analysis with async polling and SQLite cache."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .bert_pipeline import BertConfig, BertPipeline


app = FastAPI(title="Golden Reviews API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

TOPIC_EXPORT_PATH = (BASE_DIR / ".." / "topics_analizers" / "topics_export.json").resolve()


def _load_theme_lookup(path: Path) -> dict[str, dict[int, str]]:
    if not path.exists():
        return {"positive": {}, "negative": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, dict[int, str]] = {"positive": {}, "negative": {}}
    for sentiment in ("positive", "negative"):
        kept_by_theme = (data.get(sentiment) or {}).get("keptByTheme", {})
        for theme, topics in kept_by_theme.items():
            for item in topics:
                try:
                    topic_id = int(item.get("id"))
                except (TypeError, ValueError):
                    continue
                lookup[sentiment][topic_id] = theme
    return lookup


THEME_LOOKUP = _load_theme_lookup(TOPIC_EXPORT_PATH)

DB_DIR = (BASE_DIR / "analysis_output").resolve()
DB_PATH = (DB_DIR / "analysis_cache.db").resolve()

MODEL_VERSION = "bert-v2.3"
MAX_REVIEWS_DEFAULT = 1200
HIGHLIGHT_LIMIT = 6
TOPIC_LIMIT = 6
QUOTE_LIMIT = 3


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
    review_type: str = "all",
) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    seen: set[str] = set()
    cursor = "*"
    errors = 0
    max_errors = 5
    url = STEAM_REVIEWS_URL.format(app_id=app_id)

    while True:
        params = {
            "json": 1,
            "language": language,
            "review_type": review_type,
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
            if errors >= max_errors:
                break
            time.sleep(3)
            continue
        except (requests.RequestException, ValueError):
            errors += 1
            if errors >= max_errors:
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


def fetch_reviews_balanced(
    app_id: str,
    max_reviews: int = 0,
    language: str = "brazilian",
) -> list[dict[str, Any]]:
    if max_reviews < 2:
        return fetch_reviews(app_id, max_reviews, language)

    per_side = max_reviews // 2
    positive = fetch_reviews(
        app_id,
        max_reviews=per_side,
        language=language,
        review_type="positive",
    )
    negative = fetch_reviews(
        app_id,
        max_reviews=per_side,
        language=language,
        review_type="negative",
    )

    return positive + negative


def analyze_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    result = BERT_PIPELINE.analyze(reviews)
    themes = _build_theme_payload(result.get("by_topic", {}), THEME_LOOKUP)
    _write_review_dump(result.get("review_dump", []))
    return {
        "themes": themes,
        "highlights": result.get("highlights", {"positive": [], "negative": []}),
        "by_topic": result.get("by_topic", {}),
    }


def _build_theme_payload(
    by_topic: dict[str, dict[str, list[str]]],
    lookup: dict[str, dict[int, str]],
):
    entries: dict[str, dict[str, Any]] = {}

    def ensure_theme(theme: str) -> dict[str, Any]:
        if theme not in entries:
            entries[theme] = {
                "name": theme,
                "positive": {"count": 0, "examples": []},
                "negative": {"count": 0, "examples": []},
            }
        return entries[theme]

    for sentiment in ("positive", "negative"):
        topics = by_topic.get(sentiment, {})
        for topic_id, examples in topics.items():
            if str(topic_id) == "-1":
                continue
            try:
                topic_int = int(topic_id)
            except (TypeError, ValueError):
                continue
            theme = lookup.get(sentiment, {}).get(topic_int)
            if not theme:
                continue

            entry = ensure_theme(theme)
            bucket = entry[sentiment]
            bucket["count"] += len(examples)
            if len(bucket["examples"]) < 5:
                remaining = 5 - len(bucket["examples"])
                bucket["examples"].extend(examples[:remaining])

    return sorted(
        entries.values(),
        key=lambda item: item["positive"]["count"] + item["negative"]["count"],
        reverse=True,
    )


def _build_topics_payload(by_topic: dict[str, dict[str, list[str]]]):
    pos_groups = by_topic.get("positive", {})
    neg_groups = by_topic.get("negative", {})

    payload = []
    for topic_id, examples in pos_groups.items():
        if str(topic_id) == "-1":
            continue

        label = BERT_PIPELINE.topic_label(int(topic_id), "positive")
        payload.append(
            {
                "name": label,
                "positive": {"count": len(examples), "examples": examples[:5]},
                "negative": {"count": 0, "examples": []},
            }
        )

    for topic_id, examples in neg_groups.items():
        if str(topic_id) == "-1":
            continue

        label = BERT_PIPELINE.topic_label(int(topic_id), "negative")
        payload.append(
            {
                "name": label,
                "positive": {"count": 0, "examples": []},
                "negative": {"count": len(examples), "examples": examples[:5]},
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


def _init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with _get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_analysis (
                game_name TEXT PRIMARY KEY,
                status TEXT NOT NULL
                    CHECK(status IN ('processing','completed','error')),
                result_json TEXT,
                error_message TEXT,
                model_version TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_game_row(game_name: str) -> sqlite3.Row | None:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT status, result_json, error_message FROM game_analysis WHERE game_name = ?",
            (game_name,),
        ).fetchone()
    return row


def _insert_processing(game_name: str) -> bool:
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO game_analysis (
                    game_name,
                    status,
                    result_json,
                    error_message,
                    model_version
                )
                VALUES (?, 'processing', NULL, NULL, ?)
                """,
                (game_name, MODEL_VERSION),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def _update_result(game_name: str, result: dict[str, Any]) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE game_analysis
            SET
                status = 'completed',
                result_json = ?,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE game_name = ?
            """,
            (json.dumps(result, ensure_ascii=True), game_name),
        )


def _update_error(game_name: str, message: str) -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE game_analysis
            SET
                status = 'error',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE game_name = ?
            """,
            (message, game_name),
        )


def _resolve_game(game_name: str) -> dict[str, Any]:
    raw = game_name.strip()
    if not raw:
        raise ValueError("Empty game name")

    if raw.isdigit():
        details = fetch_game_details(raw)
        return {"steam_appid": int(raw), "name": details.get("name", raw)}

    params = {"term": raw, "l": "portuguese", "cc": "BR"}
    resp = requests.get(STEAM_SEARCH_URL, params=params, timeout=8)
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise ValueError("Game not found")

    appid = str(items[0].get("appid") or items[0].get("id"))
    details = fetch_game_details(appid)
    return {"steam_appid": int(appid), "name": details.get("name", raw)}


def _extract_keywords(label: str) -> list[str]:
    if ":" not in label:
        return []
    tail = label.split(":", 1)[1]
    return [w.strip() for w in tail.split(",") if w.strip()]


def _score_topic(mentions: int, max_mentions: int, sentiment: str) -> float:
    if max_mentions <= 0:
        return 3.0
    ratio = mentions / max_mentions
    if sentiment == "positive":
        score = 3.5 + (ratio * 1.5)
    else:
        score = 3.0 - (ratio * 1.5)
    return round(max(1.0, min(5.0, score)), 1)


def _build_topics_response(by_topic: dict[str, dict[str, list[str]]]) -> dict[str, Any]:
    pos_groups = by_topic.get("positive", {})
    neg_groups = by_topic.get("negative", {})
    max_pos = max((len(v) for v in pos_groups.values()), default=0)
    max_neg = max((len(v) for v in neg_groups.values()), default=0)

    positive = []
    for topic_id, examples in pos_groups.items():
        if str(topic_id) == "-1":
            continue
        label = BERT_PIPELINE.topic_label(int(topic_id), "positive")
        positive.append(
            {
                "topic": label,
                "mentions": len(examples),
                "score": _score_topic(len(examples), max_pos, "positive"),
                "keywords": _extract_keywords(label),
                "quotes": examples[:QUOTE_LIMIT],
            }
        )

    negative = []
    for topic_id, examples in neg_groups.items():
        if str(topic_id) == "-1":
            continue
        label = BERT_PIPELINE.topic_label(int(topic_id), "negative")
        negative.append(
            {
                "topic": label,
                "mentions": len(examples),
                "score": _score_topic(len(examples), max_neg, "negative"),
                "keywords": _extract_keywords(label),
                "quotes": examples[:QUOTE_LIMIT],
            }
        )

    positive = sorted(positive, key=lambda item: item["mentions"], reverse=True)[:TOPIC_LIMIT]
    negative = sorted(negative, key=lambda item: item["mentions"], reverse=True)[:TOPIC_LIMIT]
    return {"positive": positive, "negative": negative}


def process_game(game_name: str) -> dict[str, Any]:
    started = time.perf_counter()
    resolved = _resolve_game(game_name)
    appid = str(resolved["steam_appid"])
    details = fetch_game_details(appid)

    reviews = fetch_reviews_balanced(appid, max_reviews=MAX_REVIEWS_DEFAULT)
    if not reviews:
        raise RuntimeError("No reviews found")

    analysis = analyze_reviews(reviews)
    summary = summarize_reviews(reviews)

    positive_pct = summary["positive"]["percent"]
    overall_score = round(1 + (positive_pct / 100) * 4, 1)

    result = {
        "game": {
            "name": resolved["name"],
            "steam_appid": resolved["steam_appid"],
            "header_image": details.get("header_image")
            or _default_capsule(appid),
            "release_date": details.get("release_date"),
            "price": details.get("price"),
            "owners": details.get("owners"),
            "total_reviews": details.get("total_reviews"),
            "short_description": details.get("short_description"),
            "steamspy": details.get("steamspy"),
        },
        "summary": {
            "overall_score": overall_score,
            "positive_percentage": positive_pct,
            "positive_count": summary["positive"]["count"],
            "negative_percentage": summary["negative"]["percent"],
            "negative_count": summary["negative"]["count"],
            "reviews_analyzed": summary["collected"],
            "avg_hours": summary["avg_hours"],
        },
        "highlights": {
            "positive": analysis["highlights"].get("positive", [])[:HIGHLIGHT_LIMIT],
            "negative": analysis["highlights"].get("negative", [])[:HIGHLIGHT_LIMIT],
        },
        "topics": _build_topics_response(analysis["by_topic"]),
        "meta": {
            "language": "brazilian",
            "maxReviewsRequested": MAX_REVIEWS_DEFAULT,
        },
        "metadata": {
            "processing_time_seconds": round(time.perf_counter() - started, 2),
            "model_version": MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    }
    return result


def process_game_and_store(game_name: str) -> None:
    try:
        result = process_game(game_name)
        _update_result(game_name, result)
    except Exception as exc:  # noqa: BLE001
        _update_error(game_name, str(exc))


# ════════════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════════════


@app.on_event("startup")
def _startup() -> None:
    _init_db()


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "golden-reviews-api",
        "version": MODEL_VERSION,
    }


@app.get("/analyze/{game_name}")
async def analyze_endpoint(game_name: str):
    row = _fetch_game_row(game_name)
    if row:
        status = row["status"]
        if status == "completed":
            payload = json.loads(row["result_json"] or "{}")
            return JSONResponse(status_code=200, content=payload)
        if status == "processing":
            return JSONResponse(
                status_code=202,
                content={"status": "processing", "message": "Analysis in progress"},
            )
        if status == "error":
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": row["error_message"] or ""},
            )

    inserted = _insert_processing(game_name)
    if not inserted:
        row = _fetch_game_row(game_name)
        if row and row["status"] == "completed":
            payload = json.loads(row["result_json"] or "{}")
            return JSONResponse(status_code=200, content=payload)
        return JSONResponse(
            status_code=202,
            content={"status": "processing", "message": "Analysis in progress"},
        )

    asyncio.create_task(asyncio.to_thread(process_game_and_store, game_name))
    return JSONResponse(
        status_code=202,
        content={"status": "processing", "message": "Analysis in progress"},
    )


@app.get("/reviews")
def reviews_endpoint(
    appid: str = Query("", alias="appid"),
    max_reviews: int = Query(MAX_REVIEWS_DEFAULT, alias="maxReviews"),
    language: str = Query("brazilian", alias="language"),
):
    appid = appid.strip()
    if not appid:
        raise HTTPException(status_code=400, detail="appid is required")

    reviews = fetch_reviews_balanced(appid, max_reviews, language)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found")

    analysis = analyze_reviews(reviews)
    summary = summarize_reviews(reviews)
    game = fetch_game_details(appid)

    return {
        "game": game,
        "summary": summary,
        "highlights": analysis["highlights"],
        "themes": analysis["themes"],
        "meta": {"language": language, "maxReviewsRequested": max_reviews},
    }


def _default_capsule(appid: str) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_184x69.jpg"


@app.get("/search")
def search(term: str = Query("", alias="q")):
    if len(term) < 2:
        return []

    params = {"term": term, "l": "portuguese", "cc": "BR"}
    try:
        res = requests.get(STEAM_SEARCH_URL, params=params, timeout=5)
        data = res.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Steam error")

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
        results.append({"appid": appid, "name": item.get("name"), "image": image})

    return results