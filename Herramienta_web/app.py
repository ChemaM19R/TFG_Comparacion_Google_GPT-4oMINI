import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional
from collections import Counter
import base64
from dotenv import load_dotenv
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)
def openai_login():
    load_dotenv("exampe_apis.env")
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    return client

# Configura la API key directamente en la llamada
client = openai_login()

# ── DataForSEO ──────────────────────────────────

DATAFORSEO_URL      = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


DATAFORSEO_LOGIN = ""
DATAFORSEO_PASSWORD = ""
auth = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()

DATAFORSEO_HEADERS = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

LIMIT = 10


# ─────────────────────────────────────────────
# PYDANTIC MODEL
# ─────────────────────────────────────────────
class LinkItem(BaseModel):
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None


class LinksResponse(BaseModel):
    links: list[LinkItem]


# ─────────────────────────────────────────────
# SERP GOOGLE · DataForSEO
# ─────────────────────────────────────────────
def consultar_google_serp(consulta: str) -> list[dict]:
    """Consulta DataForSEO SERP API — España (location_code 2724)."""
    payload = [{
        "keyword": consulta,
        "language_code": "es",
        "location_code": 2724,   # España
        "device": "desktop",
        "depth": LIMIT,
    }]
    try:
        response = requests.post(
            DATAFORSEO_URL,
            headers=DATAFORSEO_HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        task = data["tasks"][0]
        status_code = task.get("status_code", 0)
        if status_code != 20000:
            print(f"⚠️ DataForSEO task error {status_code}: {task.get('status_message')}")
            return []

        items = task["result"][0]["items"]
        organic = [
            {
                "rank":    item.get("rank_group", idx + 1),
                "url":     item.get("url", ""),
                "title":   item.get("title", ""),
                "snippet": item.get("description", ""),
            }
            for idx, item in enumerate(items)
            if item.get("type") == "organic" and item.get("url")
        ]
        return organic[:LIMIT]

    except Exception as e:
        print(f"⚠️ Error consultando DataForSEO para '{consulta}': {e}")
        return []


# ─────────────────────────────────────────────
# GPT CON SEARCH (web_search tool)
# ─────────────────────────────────────────────
def consultar_gpt_con_search(texto_consulta: str) -> list[dict]:
    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": texto_consulta}],
                }
            ],
            reasoning={},
            tools=[
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate",
                        "country": "ES",
                        "region": "España",
                        "city": "España",
                    },
                    "search_context_size": "medium",
                }
            ],
            temperature=0,
            max_output_tokens=2048,
            top_p=1,
            store=True,
            include=["web_search_call.action.sources"],
            text_format=LinksResponse,
        )
        parsed: LinksResponse = response.output_parsed
        if parsed is None:
            return []
        return [
            {"url": l.url, "title": l.title or "", "snippet": l.snippet or ""}
            for l in parsed.links
        ]
    except Exception as e:
        print(f"⚠️ Error GPT con search: {e}")
        return []


# ─────────────────────────────────────────────
# GPT SIN SEARCH
# ─────────────────────────────────────────────
def consultar_gpt_sin_search(texto_consulta: str) -> list[dict]:
    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": texto_consulta}],
                }
            ],
            reasoning={},
            tools=[],
            temperature=0,
            max_output_tokens=2048,
            top_p=1,
            store=True,
            text_format=LinksResponse,
        )
        parsed: LinksResponse = response.output_parsed
        if parsed is None:
            return []
        return [
            {"url": l.url, "title": l.title or "", "snippet": l.snippet or ""}
            for l in parsed.links
        ]
    except Exception as e:
        print(f"⚠️ Error GPT sin search: {e}")
        return []


# ─────────────────────────────────────────────
# ANÁLISIS DE COINCIDENCIAS Y RANKING
# ─────────────────────────────────────────────
def normalizar_url(url: str) -> str:
    """Normaliza la URL para comparación (quita trailing slash, www, protocolo)."""
    url = url.strip().lower()
    for prefix in ["https://", "http://"]:
        if url.startswith(prefix):
            url = url[len(prefix):]
    if url.startswith("www."):
        url = url[4:]
    return url.rstrip("/")


def calcular_ranking_y_analisis(
    google_results: list[dict],
    gpt_search_results: list[dict],
    gpt_nosearch_results: list[dict],
) -> dict:
    """
    Asigna puntos a cada URL según su posición en cada fuente y calcula coincidencias.
    Puntuación: posición 1 → 10 pts, posición 2 → 9 pts, …, posición 10 → 1 pt
    """
    all_sources = {
        "google_serp": google_results,
        "gpt_con_search": gpt_search_results,
        "gpt_sin_search": gpt_nosearch_results,
    }

    # Mapeo url_normalizada → url_original + datos
    url_data: dict[str, dict] = {}
    url_scores: Counter = Counter()
    url_sources: dict[str, list[str]] = {}

    for source_name, results in all_sources.items():
        for pos, item in enumerate(results):
            norm = normalizar_url(item["url"])
            if not norm:
                continue
            score = max(0, LIMIT - pos)  # pos=0 → 10, pos=9 → 1
            url_scores[norm] += score

            if norm not in url_data:
                url_data[norm] = {
                    "url": item["url"],
                    "title": item.get("title") or "",
                    "snippet": item.get("snippet") or "",
                }
            # Enriquecer datos si vienen vacíos
            if not url_data[norm]["title"] and item.get("title"):
                url_data[norm]["title"] = item["title"]
            if not url_data[norm]["snippet"] and item.get("snippet"):
                url_data[norm]["snippet"] = item["snippet"]

            if norm not in url_sources:
                url_sources[norm] = []
            url_sources[norm].append(source_name)

    # Ranking global
    ranking = []
    for norm, score in url_scores.most_common(20):
        sources = url_sources.get(norm, [])
        ranking.append(
            {
                "url": url_data[norm]["url"],
                "title": url_data[norm]["title"],
                "snippet": url_data[norm]["snippet"],
                "score": score,
                "sources": sources,
                "coincidencias": len(sources),
                "aparece_en": ", ".join(sources),
            }
        )

    # Stats de coincidencias
    total_urls = len(url_data)
    urls_en_todas = sum(1 for s in url_sources.values() if len(s) == 3)
    urls_en_dos = sum(1 for s in url_sources.values() if len(s) == 2)
    urls_en_una = sum(1 for s in url_sources.values() if len(s) == 1)

    # Coincidencias entre pares
    norm_google = {normalizar_url(r["url"]) for r in google_results if r.get("url")}
    norm_gpt_s = {normalizar_url(r["url"]) for r in gpt_search_results if r.get("url")}
    norm_gpt_ns = {normalizar_url(r["url"]) for r in gpt_nosearch_results if r.get("url")}

    analisis = {
        "total_urls_unicas": total_urls,
        "en_las_3_fuentes": urls_en_todas,
        "en_2_fuentes": urls_en_dos,
        "en_1_sola_fuente": urls_en_una,
        "coincidencias_google_vs_gpt_search": len(norm_google & norm_gpt_s),
        "coincidencias_google_vs_gpt_nosearch": len(norm_google & norm_gpt_ns),
        "coincidencias_gpt_search_vs_gpt_nosearch": len(norm_gpt_s & norm_gpt_ns),
        "conteo_por_fuente": {
            "google_serp": len(google_results),
            "gpt_con_search": len(gpt_search_results),
            "gpt_sin_search": len(gpt_nosearch_results),
        },
    }

    return {"ranking": ranking, "analisis": analisis}


# ─────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────
@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()

    if not query:
        return jsonify({"error": "La consulta no puede estar vacía"}), 400

    print(f"\n🔍 Consulta recibida: {query}")

    # Llamadas a las 3 fuentes
    google_results = consultar_google_serp(query)
    print(f"  ✅ SERP Google: {len(google_results)} resultados")

    gpt_search_results = consultar_gpt_con_search(query)
    print(f"  ✅ GPT con search: {len(gpt_search_results)} resultados")

    gpt_nosearch_results = consultar_gpt_sin_search(query)
    print(f"  ✅ GPT sin search: {len(gpt_nosearch_results)} resultados")

    # Calcular ranking y análisis
    resultado = calcular_ranking_y_analisis(
        google_results, gpt_search_results, gpt_nosearch_results
    )

    return jsonify(
        {
            "query": query,
            "fuentes": {
                "google_serp": google_results,
                "gpt_con_search": gpt_search_results,
                "gpt_sin_search": gpt_nosearch_results,
            },
            "ranking": resultado["ranking"],
            "analisis": resultado["analisis"],
        }
    )


@app.route("/api/url-report", methods=["POST"])
def url_report():
    """
    Dado una query + una URL objetivo, devuelve:
    - posición de la URL en Google SERP (o None)
    - posición en GPT con Search (o None)
    - posición en GPT sin Search (o None)
    - los resultados completos de cada fuente
    """
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    target_url = (data.get("url") or "").strip()

    if not query:
        return jsonify({"error": "La consulta no puede estar vacía"}), 400
    if not target_url:
        return jsonify({"error": "La URL no puede estar vacía"}), 400

    print(f"\n🎯 URL Report — query: '{query}' | url: '{target_url}'")

    google_results    = consultar_google_serp(query)
    gpt_search_results   = consultar_gpt_con_search(query)
    gpt_nosearch_results = consultar_gpt_sin_search(query)

    norm_target = normalizar_url(target_url)

    def find_position(results):
        for i, r in enumerate(results):
            if normalizar_url(r.get("url", "")) == norm_target:
                return i + 1   # 1-based
        return None

    pos_google    = find_position(google_results)
    pos_gpt_s     = find_position(gpt_search_results)
    pos_gpt_ns    = find_position(gpt_nosearch_results)

    # Snippet/title de la URL objetivo si aparece en alguna fuente
    meta = {}
    for r in google_results + gpt_search_results + gpt_nosearch_results:
        if normalizar_url(r.get("url", "")) == norm_target:
            meta = {"title": r.get("title", ""), "snippet": r.get("snippet", "")}
            break

    return jsonify({
        "query": query,
        "target_url": target_url,
        "meta": meta,
        "posiciones": {
            "google_serp":    pos_google,
            "gpt_con_search": pos_gpt_s,
            "gpt_sin_search": pos_gpt_ns,
        },
        "fuentes": {
            "google_serp":    google_results,
            "gpt_con_search": gpt_search_results,
            "gpt_sin_search": gpt_nosearch_results,
        },
    })


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Servidor iniciado en http://127.0.0.1:5000")
    print("📡 SERP: DataForSEO API · España (location_code 2724)")
    app.run(debug=True, port=5000)