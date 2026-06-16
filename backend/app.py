from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline_online import ABSAPipeline
from llm_summary import gerar_resumo

steam_session = requests.Session()

app = FastAPI(title="Golden Reviews API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CONFIG & DB
STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
STEAM_DETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={app_id}&l=portuguese"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
STEAMSPY_DETAILS_URL = "https://steamspy.com/api.php"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "cache.db"

MODEL_PATH = str(BASE_DIR / "steam_bertopic_model")
PIPELINE = ABSAPipeline(MODEL_PATH)


def init_db():
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
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

# HELPER FUNCTIONS
def fetch_game_details(app_id: str) -> dict[str, Any]:
    steamspy_data = fetch_steamspy_stats(app_id)
    try:
        resp = steam_session.get(
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
        resp = steam_session.get(STEAMSPY_DETAILS_URL, params=params, timeout=8)
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

    loop_count = 0 

    while True:
        loop_count += 1
        if loop_count > 150: 
            print(f"\n[Aviso] Quebra de segurança acionada! A Steam entrou em loop no appid {app_id}.")
            break

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
            resp = steam_session.get(url, params=params, timeout=15)
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

        if loop_count % 5 == 0:
            print(f"      -> Steam: Baixando reviews... {len(reviews)} coletadas até agora.")
        novo_cursor = data.get("cursor", "")
        if not novo_cursor or novo_cursor == cursor:
            break

        cursor = novo_cursor
        time.sleep(0.35)

    return reviews

def _background_analysis_task(appid: str, max_reviews: int, language: str):
    try:
        print(f"[Worker] Fetching reviews para appid={appid}...")
        reviews = fetch_reviews(appid, max_reviews, language)
        game_details = fetch_game_details(appid)
        
        if not reviews:
            with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
                conn.execute("UPDATE game_cache SET status='error', data=?, updated_at=? WHERE appid=?",
                             ('{"error": "Nenhuma review encontrada."}', time.time(), appid))
            return
            
        print(f"[Worker] Iniciando ABSA Pipeline para appid={appid} com {len(reviews)} reviews...")
        analysis_result = PIPELINE.process_reviews(reviews, game_details)
        
        analysis_result["game"] = {**analysis_result.get("game", {}), **game_details}

        topicos_positivos = analysis_result.get("topics", {}).get("positive", [])
        topicos_negativos = analysis_result.get("topics", {}).get("negative", [])

        frases_positivas = sum(t.get("mentions", 0) for t in topicos_positivos)
        frases_negativas = sum(t.get("mentions", 0) for t in topicos_negativos)
        total_frases = frases_positivas + frases_negativas

        pct_positiva = round((frases_positivas / total_frases) * 100) if total_frases > 0 else 0
        pct_negativa = round((frases_negativas / total_frases) * 100) if total_frases > 0 else 0

        total_reviews_baixadas = len(reviews)
        avg_hours = sum(r.get("hours", 0) for r in reviews) / total_reviews_baixadas if total_reviews_baixadas > 0 else 0
        
        if "summary" not in analysis_result:
            analysis_result["summary"] = {}
            
        analysis_result["summary"].update({
            "avg_hours": avg_hours,
            "sentences_positive_count": frases_positivas,
            "sentences_negative_count": frases_negativas,
            "sentences_positive_percentage": pct_positiva,
            "sentences_negative_percentage": pct_negativa,
            "total_extracted_sentences": total_frases
        })

        print(f"[Worker] Gerando resumo em linguagem natural via LLM...")

        try:
            texto_resumo = gerar_resumo(analysis_result)
        except Exception as llm_err:
            print(f"[Worker] LLM indisponível ({llm_err}). Gerando resumo estatístico padrão...")

            score_final = analysis_result["summary"].get("overall_score", 0.0)
            total_revs = analysis_result["summary"].get("reviews_analyzed", 0)
            pct_pos = analysis_result["summary"].get("positive_percentage", 0)

            texto_resumo = (
                f"Análise baseada em {total_revs} reviews recentes da Steam. "
                f"O jogo apresenta um índice de aprovação de {pct_pos}% pelos usuários, "
                f"com uma nota de sentimento calculada em {score_final}/5.0 baseada nos tópicos identificados."
            )

        analysis_result["summary"]["ai_text_summary"] = texto_resumo

        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute("UPDATE game_cache SET status='completed', data=?, updated_at=? WHERE appid=?",
                         (json.dumps(analysis_result), time.time(), appid))
                         
        print(f"[Worker] Modelagem concluída para appid={appid}!")

    except Exception as e:
        print(f"[Worker] Error processando appid={appid}: {e}")
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute("UPDATE game_cache SET status='error', data=?, updated_at=? WHERE appid=?",
                         (json.dumps({"error": str(e)}), time.time(), appid))

def _background_llm_recovery(appid: str, data_dict: dict):
    try:
        print(f"[Worker LLM] Re-analisando AppID {appid} via Groq...")
        
        texto_resumo = gerar_resumo(data_dict)
        data_dict["summary"]["ai_text_summary"] = texto_resumo
        
        # Salva de volta no banco
        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute("UPDATE game_cache SET status='completed', data=?, updated_at=? WHERE appid=?",
                         (json.dumps(data_dict), time.time(), appid))
            
        print(f"[Worker LLM] AppID {appid} curado com sucesso!")
        
    except Exception as e:
        print(f"[Worker LLM] Falha na recuperação: {e}")

        with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
            conn.execute("UPDATE game_cache SET status='completed' WHERE appid=?", (appid,))

def _default_capsule(appid: str) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/capsule_184x69.jpg"

# ROUTES
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
    maxReviews: int = Query(1000, description="Nº máximo de reviews"),
    language: str = Query("brazilian", description="Idioma das reviews")
):
    appid = appid.strip()
    if not appid:
        return JSONResponse(status_code=400, content={"error": "Parâmetro 'appid' é obrigatório."})
    
    maxReviews = 1000 #Trava de segurança 

    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.execute("SELECT status, data FROM game_cache WHERE appid = ?", (appid,))
        row = cursor.fetchone()

        if row:
            status, data_str = row
            if status == "completed":
                # 1. Transforma a string do banco num dicionário real (isso resolve o problema dos acentos)
                dados_json = json.loads(data_str)
                
                # 2. Navega até onde o texto da IA está salvo
                summary = dados_json.get("summary", {})
                ai_text_obj = summary.get("ai_text_summary", "")
                
                texto_resumo = ""
                if isinstance(ai_text_obj, dict):
                    texto_resumo = ai_text_obj.get("resumo", "").lower()
                elif isinstance(ai_text_obj, str):
                    texto_resumo = ai_text_obj.lower()
                
                # 3. Verifica o erro no texto já extraído e limpo
                if "indisponível" in texto_resumo or "limite de requisições" in texto_resumo:
                    print(f"[Auto-cura] Acionando recuperação LLM para o appid {appid}.")
                    
                    conn.execute("UPDATE game_cache SET status='processing' WHERE appid=?", (appid,))
                    
                    background_tasks.add_task(_background_llm_recovery, appid, dados_json)
                    
                    return JSONResponse(
                        status_code=202,
                        content={
                            "status": "processing",
                            "message": "Re-conectando com a Inteligência Artificial. Aguarde..."
                        }
                    )
                else:
                    return JSONResponse(content=dados_json)
                    
            elif status == "error":
                 return JSONResponse(status_code=500, content=json.loads(data_str))
                 
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

@app.get("/recommended")
def recommended_games():
    games = []
    with sqlite3.connect(DB_PATH, timeout=10.0) as conn:
        cursor = conn.execute(
            "SELECT data FROM game_cache WHERE status = 'completed' ORDER BY updated_at DESC LIMIT 100"
        )
        for row in cursor:
            try:
                game_data = json.loads(row[0])
                game_info = game_data.get("game", {})
                
                appid = game_info.get("appid")
                if not appid:
                    continue
                    
                image = game_info.get("header_image")
                if not image:
                    image = _default_capsule(str(appid))
                    
                games.append({
                    "appid": str(appid),
                    "name": game_info.get("name", f"App {appid}"),
                    "image": image
                })
            except Exception:
                continue
                
    return games


@app.get("/search")
def search(q: str = Query("", description="Termo de pesquisa", alias="q")):
    term = q.strip()
    if len(term) < 2:
        return []

    params = {"term": term, "l": "portuguese", "cc": "BR"}
    try:
        res = steam_session.get(STEAM_SEARCH_URL, params=params, timeout=5)
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
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000, 
        reload=False,
        workers=1,
    )
