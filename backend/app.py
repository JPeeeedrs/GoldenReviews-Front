"""FastAPI backend para análise de reviews da Steam com cache SQLite (WAL) e ABSA."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline_online import ABSAPipeline

from llm_summary import gerar_resumo

app = FastAPI(title="Golden Reviews API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ════════════════════════════════════════════════════════════════════════════
# CONFIG & DB
# ════════════════════════════════════════════════════════════════════════════

STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={app_id}&l=portuguese"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAMSPY_DETAILS_URL = "https://steamspy.com/api.php"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"

MODEL_PATH = str(BASE_DIR / "steam_bertopic_model")
PIPELINE = ABSAPipeline(MODEL_PATH)


def init_db():
    """Inicializa o banco de dados SQLite com suporte a concorrência."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_cache (
                appid TEXT PRIMARY KEY,
                status TEXT,
                data TEXT,
                updated_at REAL
            )
            """
        )

init_db()

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

def _background_analysis_task(appid: str, max_reviews: int, language: str):
    """Worker Thread para evitar bloqueio do event loop do FastAPI"""
    try:
        print(f"[Worker] Fetching reviews para appid={appid}...")
        reviews = fetch_reviews(appid, max_reviews, language)
        game_details = fetch_game_details(appid)
        
        if not reviews:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE game_cache SET status='error', data=?, updated_at=? WHERE appid=?",
                             ('{"error": "Nenhuma review encontrada."}', time.time(), appid))
            return
            
        print(f"[Worker] Iniciando ABSA Pipeline para appid={appid} com {len(reviews)} reviews...")
        analysis_result = PIPELINE.process_reviews(reviews, game_details)
        
        analysis_result["game"] = {**analysis_result.get("game", {}), **game_details}

        # ------------------------------------------------------------------
        # FIX: Restaurando a matemática do Summary que o Front espera
        # ------------------------------------------------------------------
        total = len(reviews)
        pos_count = sum(1 for r in reviews if r.get("recommended"))
        neg_count = total - pos_count
        
        pos_pct = round((pos_count / total) * 100) if total > 0 else 0
        neg_pct = round((neg_count / total) * 100) if total > 0 else 0
        avg_hours = sum(r.get("hours", 0) for r in reviews) / total if total > 0 else 0
        
        if "summary" not in analysis_result:
            analysis_result["summary"] = {}
            
        # Atualiza o summary com os dados crus da Steam preservando o que a IA gerou
        analysis_result["summary"].update({
            "reviews_analyzed": total,
            "positive_count": pos_count,
            "positive_percentage": pos_pct,
            "negative_count": neg_count,
            "negative_percentage": neg_pct,
            "avg_hours": avg_hours
        })
        # ------------------------------------------------------------------

        # ==================================================================
        print(f"[Worker] Gerando resumo em linguagem natural via LLM...")
        texto_resumo = gerar_resumo(analysis_result)
        analysis_result["summary"]["ai_text_summary"] = texto_resumo

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE game_cache SET status='completed', data=?, updated_at=? WHERE appid=?",
                         (json.dumps(analysis_result), time.time(), appid))
                         
        print(f"[Worker] Modelagem concluída para appid={appid}!")

    except Exception as e:
        print(f"[Worker] Error processando appid={appid}: {e}")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE game_cache SET status='error', data=?, updated_at=? WHERE appid=?",
                         (json.dumps({"error": str(e)}), time.time(), appid))

def _default_capsule(appid: str) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_184x69.jpg"


# ════════════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "golden-reviews-api"
    }

@app.get("/reviews")
def reviews_endpoint(
    background_tasks: BackgroundTasks, 
    appid: str = Query(..., description="App ID na Steam"),
    maxReviews: int = Query(1200, description="Nº máximo de reviews"),
    language: str = Query("brazilian", description="Idioma das reviews")
):
    appid = appid.strip()
    if not appid:
        return JSONResponse(status_code=400, content={"error": "Parâmetro 'appid' é obrigatório."})

    # Consulta ao Cache (Catraca do Polling)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT status, data FROM game_cache WHERE appid = ?", (appid,))
        row = cursor.fetchone()

        if row:
            status, data = row
            if status == "completed":
                return JSONResponse(content=json.loads(data))
            elif status == "error":
                 return JSONResponse(status_code=500, content=json.loads(data))
            elif status == "processing":
                 return JSONResponse(
                     status_code=202,
                     content={
                         "status": "processing",
                         "message": "Análise da Inteligência em andamento. Continue consultando."
                     }
                 )

        # Se não existe no cache, vamos engatilhar a Análise Background
        conn.execute(
            "INSERT INTO game_cache (appid, status, data, updated_at) VALUES (?, ?, ?, ?)",
            (appid, "processing", "", time.time())
        )
        
    # Dispara a Fila de Espera (Worker CPU-bound)
    background_tasks.add_task(_background_analysis_task, appid, maxReviews, language)

    return JSONResponse(
         status_code=202,
         content={
             "status": "processing",
             "message": "A Análise da inteligência começou agora. Continue consultando."
         }
    )


@app.get("/search")
def search(q: str = Query("", description="Termo de pesquisa", alias="q")):
    term = q.strip()
    if len(term) < 2:
        return []

    params = {"term": term, "l": "portuguese", "cc": "BR"}
    try:
        res = requests.get(STEAM_SEARCH_URL, params=params, timeout=5)
        data = res.json()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Erro na comunicação com a Steam")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)